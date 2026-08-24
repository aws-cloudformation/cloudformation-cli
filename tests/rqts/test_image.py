"""Tests for RQTS image resolution and pull-with-retry.

These tests exercise ``rpdk.core.rqts.image`` (design Properties 1-2, plus the
pull-exhaustion edge cases and the cached-image fallback branch). The pull is
attempted on every run (mutable ``latest`` semantics); on exhaustion the run
falls back to a cached local image with a warning and fails only when no
cached copy exists. Docker is never actually invoked: the single internal
``_run_docker`` seam and ``image_present_locally`` are patched so the retry
policy can be driven deterministically and kept fast.

Library: Hypothesis (the standard Python property-based testing library). Each
property test runs at least 100 generated examples via
``@settings(max_examples=100)`` and is tagged with a comment referencing the
design property it validates.
"""
import subprocess
from types import SimpleNamespace
from unittest import mock

import pytest
from hypothesis import given, settings, strategies as st

from rpdk.core.exceptions import SysExitRecommendedError
from rpdk.core.rqts import image as image_module
from rpdk.core.rqts.constants import PULL_MAX_ATTEMPTS, RQTS_IMAGE_REFERENCE

# A marker used to build distinctive, searchable fake credential values. It is
# made of characters that never appear in the generated image references, so the
# credential values can be located reliably (or, as Property 2 requires,
# confirmed absent) anywhere in the recorded docker invocations.
_SECRET_MARKER = "AWSSECRETMARKER"

# AWS credential environment variable names that must never be threaded into an
# anonymous ``docker pull``.
_AWS_CRED_TOKENS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    _SECRET_MARKER,
)

_IMAGE_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789./:-"

# Image references, including the empty string and freely generated refs, so the
# resolution property covers both the override and the pinned-default cases.
image_refs = st.text(alphabet=_IMAGE_ALPHABET, min_size=1, max_size=60)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _RecordingDocker:
    """A fake ``_run_docker`` that records calls and replays a fixed result seq.

    Each queued result is either a ``returncode`` int (wrapped in a
    ``CompletedProcess``) or an exception instance to raise, modelling docker
    pull failures/timeouts and successes.
    """

    def __init__(self, results):
        self._results = list(results)
        self.calls = []

    def __call__(self, docker_args, timeout=None):
        self.calls.append(
            SimpleNamespace(docker_args=list(docker_args), timeout=timeout)
        )
        result = self._results[len(self.calls) - 1]
        if isinstance(result, BaseException):
            raise result
        return subprocess.CompletedProcess(
            args=["docker", *docker_args],
            returncode=result,
            stdout=b"",
            stderr=b"" if result == 0 else b"boom",
        )


def _make_args(rqts_image=None):
    return SimpleNamespace(rqts_image=rqts_image)


# ===========================================================================
# Task 4.2 -> Property 1
# ===========================================================================
# Feature: cfn-test-v2-flag, Property 1: Image resolution honors override, else pinned default
@settings(max_examples=100)
@given(override=st.one_of(st.none(), st.just(""), image_refs))
def test_property_1_image_resolution_override_else_default(override):
    """resolve_image returns the override when non-empty, else the pinned default.

    Validates: Requirements 2.1, 2.2
    """
    args = _make_args(rqts_image=override)

    resolved = image_module.resolve_image(args)

    if override:
        assert resolved == override
    else:
        assert resolved == RQTS_IMAGE_REFERENCE


def test_resolve_image_missing_attribute_uses_default():
    """resolve_image tolerates args without an ``rqts_image`` attribute."""
    assert image_module.resolve_image(SimpleNamespace()) == RQTS_IMAGE_REFERENCE


# ===========================================================================
# Task 4.3 -> Property 2
# ===========================================================================
def _expected_attempts(results):
    """Model the bounded retry policy: attempt until first success, capped."""
    for index, result in enumerate(results[:PULL_MAX_ATTEMPTS]):
        if result == 0:
            return index + 1, True
    return min(len(results), PULL_MAX_ATTEMPTS), False


@st.composite
def pull_result_sequences(draw):
    """Generate a sequence of per-attempt pull outcomes.

    Each element is a ``0`` (success), a non-zero return code (failure), or an
    exception instance (timeout / spawn error). The sequence is padded to at
    least ``PULL_MAX_ATTEMPTS`` so ``ensure_image`` always has an outcome to
    consume even when every attempt fails.
    """
    outcome = st.one_of(
        st.just(0),
        st.integers(min_value=1, max_value=255),
        st.just(subprocess.TimeoutExpired(cmd="docker pull", timeout=1)),
        st.just(OSError("docker not found")),
    )
    seq = draw(
        st.lists(outcome, min_size=PULL_MAX_ATTEMPTS, max_size=PULL_MAX_ATTEMPTS + 4)
    )
    return seq


# Feature: cfn-test-v2-flag, Property 2: Image pull is bounded and anonymous
@settings(max_examples=100)
@given(results=pull_result_sequences(), image_ref=image_refs, cached=st.booleans())
def test_property_2_pull_is_bounded_and_anonymous(results, image_ref, cached):
    """ensure_image pulls at most PULL_MAX_ATTEMPTS regardless of the local
    cache state, stops on first success, never supplies AWS credentials to the
    pull, falls back to a cached image on exhaustion, and raises only when no
    cached copy exists.

    Validates: Requirements 2.3, 2.4, 2.5, 2.6
    """
    fake_docker = _RecordingDocker(results)
    expected_attempts, should_succeed = _expected_attempts(results)

    # ``mock.patch`` context managers are used (rather than the monkeypatch
    # fixture) so the patches are applied and reset for every generated example.
    with mock.patch.object(
        image_module, "image_present_locally", lambda ref: cached
    ), mock.patch.object(image_module, "_run_docker", fake_docker):
        if should_succeed or cached:
            image_module.ensure_image(image_ref)
        else:
            with pytest.raises(SysExitRecommendedError):
                image_module.ensure_image(image_ref)

    # Bounded: pull is attempted at most PULL_MAX_ATTEMPTS times, and exactly the
    # number of attempts the retry policy predicts (stopping on first success).
    assert len(fake_docker.calls) <= PULL_MAX_ATTEMPTS
    assert len(fake_docker.calls) == expected_attempts

    for call in fake_docker.calls:
        # Every invocation is an anonymous ``docker pull <ref>`` for this image.
        assert call.docker_args[0] == "pull"
        assert image_ref in call.docker_args

        # No AWS credential is ever threaded through: neither positionally in the
        # docker args nor via any keyword. ensure_image only passes ``timeout``.
        for token in call.docker_args:
            for cred in _AWS_CRED_TOKENS:
                assert cred not in token


# ===========================================================================
# Task 4.4 -> pull-exhaustion edge cases
# ===========================================================================
def test_pull_exhaustion_without_cached_image_raises(monkeypatch):
    """Pull fails on all attempts with no cached image -> SysExitRecommendedError
    after exactly PULL_MAX_ATTEMPTS attempts.

    Validates: Requirements 2.6
    """
    # Every attempt fails with a non-zero return code.
    fake_docker = _RecordingDocker([1] * (PULL_MAX_ATTEMPTS + 2))
    monkeypatch.setattr(image_module, "image_present_locally", lambda ref: False)
    monkeypatch.setattr(image_module, "_run_docker", fake_docker)

    with pytest.raises(SysExitRecommendedError):
        image_module.ensure_image("some/image:tag")

    assert len(fake_docker.calls) == PULL_MAX_ATTEMPTS


def test_pull_exhaustion_with_cached_image_falls_back_with_warning(monkeypatch, caplog):
    """Pull fails on all attempts but the image is cached locally -> warn and
    run from the local store instead of raising.

    Validates: Requirements 2.5
    """
    fake_docker = _RecordingDocker([1] * PULL_MAX_ATTEMPTS)
    monkeypatch.setattr(image_module, "image_present_locally", lambda ref: True)
    monkeypatch.setattr(image_module, "_run_docker", fake_docker)

    with caplog.at_level("WARNING", logger=image_module.__name__):
        image_module.ensure_image("cached/image:tag")

    # All attempts consumed, then fallback: no exception raised.
    assert len(fake_docker.calls) == PULL_MAX_ATTEMPTS
    assert any(
        "cached" in record.getMessage() and "cached/image:tag" in record.getMessage()
        for record in caplog.records
    )


def test_pull_exhaustion_on_repeated_timeouts(monkeypatch):
    """Repeated per-attempt timeouts also exhaust after exactly PULL_MAX_ATTEMPTS."""
    timeouts = [
        subprocess.TimeoutExpired(cmd="docker pull", timeout=1)
        for _ in range(PULL_MAX_ATTEMPTS + 1)
    ]
    fake_docker = _RecordingDocker(timeouts)
    monkeypatch.setattr(image_module, "image_present_locally", lambda ref: False)
    monkeypatch.setattr(image_module, "_run_docker", fake_docker)

    with pytest.raises(SysExitRecommendedError):
        image_module.ensure_image("some/image:tag")

    assert len(fake_docker.calls) == PULL_MAX_ATTEMPTS


# ===========================================================================
# Task 4.5 -> pull-first behavior
# ===========================================================================
def test_ensure_image_present_locally_still_pulls(monkeypatch):
    """Image present locally -> ensure_image STILL attempts the pull, so a moved
    mutable tag (e.g. latest) is refreshed without manual docker pull.

    Validates: Requirements 2.3
    """
    fake_docker = _RecordingDocker([0])
    monkeypatch.setattr(image_module, "image_present_locally", lambda ref: True)
    monkeypatch.setattr(image_module, "_run_docker", fake_docker)

    image_module.ensure_image("present/image:tag")

    # Exactly one successful pull attempt; presence never short-circuits it.
    assert len(fake_docker.calls) == 1
    assert fake_docker.calls[0].docker_args[0] == "pull"
    assert "present/image:tag" in fake_docker.calls[0].docker_args


def test_ensure_image_absent_pulls_then_returns(monkeypatch):
    """Image absent -> ensure_image pulls, then returns on success.

    Validates: Requirements 2.3, 2.4
    """
    fake_docker = _RecordingDocker([0])
    monkeypatch.setattr(image_module, "image_present_locally", lambda ref: False)
    monkeypatch.setattr(image_module, "_run_docker", fake_docker)

    image_module.ensure_image("absent/image:tag")

    assert len(fake_docker.calls) == 1
    assert fake_docker.calls[0].docker_args[0] == "pull"
    assert "absent/image:tag" in fake_docker.calls[0].docker_args


def test_image_present_locally_uses_docker_image_inspect(monkeypatch):
    """image_present_locally maps ``docker image inspect`` exit status to bool."""
    present = _RecordingDocker([0])
    monkeypatch.setattr(image_module, "_run_docker", present)
    assert image_module.image_present_locally("ref:tag") is True
    assert present.calls[0].docker_args == ["image", "inspect", "ref:tag"]

    absent = _RecordingDocker([1])
    monkeypatch.setattr(image_module, "_run_docker", absent)
    assert image_module.image_present_locally("ref:tag") is False
