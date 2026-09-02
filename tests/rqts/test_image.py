"""Tests for :class:`rpdk.core.rqts.image.RqtsImage`.

Covers image resolution (Property 1), the bounded anonymous pull with its
cached-image fallback (Property 2), the ``docker run`` argument/environment
construction (Properties 4-12), and running the container.

Docker is never actually invoked: the single ``_run_docker`` seam is patched so
the retry policy and the container run can be driven deterministically, and the
one test that reaches ``subprocess.run`` patches it.

Library: Hypothesis (the standard Python property-based testing library). Each
property test runs at least 100 generated examples via
``@settings(max_examples=100)`` and is tagged with a comment referencing the
design property it validates.
"""

import json
import subprocess
from types import SimpleNamespace
from unittest import mock

import pytest
from hypothesis import given, settings, strategies as st

from rpdk.core.exceptions import SysExitRecommendedError
from rpdk.core.rqts import image as image_module
from rpdk.core.rqts.constants import (
    CALLER_ENV_CRED_KEYS,
    CONTAINER_OUTPUT_DIR,
    CONTAINER_WORKDIR,
    ENV_CRED_KEYS,
    ENV_TYPE_CONFIGURATION,
    EXTENSION_CONTRACT_TESTS,
    HOST_OUTPUT_DIRNAME,
    PULL_MAX_ATTEMPTS,
    RQTS_IMAGE_REFERENCE,
)
from rpdk.core.rqts.image import RqtsImage

# The CLI default region: ``cfn test`` defines ``--region`` with this default, so
# the effective region is always populated even when the user omits ``--region``.
CLI_DEFAULT_REGION = "us-east-1"

# A marker used to build distinctive, searchable fake credential values, made of
# characters that never appear in generated image references, regions or names,
# so a secret can be confirmed absent anywhere in the docker arguments.
_SECRET_MARKER = "AWSSECRETMARKER"

# Credential environment variable names that must never be threaded into an
# anonymous ``docker pull``.
_AWS_CRED_TOKENS = ENV_CRED_KEYS + CALLER_ENV_CRED_KEYS + (_SECRET_MARKER,)

# Flags the DirectJar contract must NEVER emit (they belong to the old SAM Local
# / remote-lambda shapes).
FORBIDDEN_FLAGS = ("--handler-jar", "-h", "-tn", "--sam-local", "--remote-lambda")

# The tagging scenarios that ``cfn test --v2`` must NEVER run.
FORBIDDEN_TAGGING_SCENARIOS = (
    "tagging-oob",
    "tagging-permission",
    "tagging-stack",
    "tagging-system",
)

# Fixed credentials for the tests that do not exercise credential handling.
CREDS = dict(zip(ENV_CRED_KEYS, ("AKID", "SECRET", "TOKEN")))

_IMAGE_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789./:-"
_SEGMENT_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# Image references, including the empty string, so resolution covers both the
# override and the pinned-default cases.
image_refs = st.text(alphabet=_IMAGE_ALPHABET, min_size=1, max_size=60)

_segments = st.text(alphabet=_SEGMENT_ALPHABET, min_size=1, max_size=12)

_KNOWN_REGIONS = [
    CLI_DEFAULT_REGION,
    "us-west-2",
    "eu-west-1",
    "ap-southeast-2",
    "eu-central-1",
]
regions = st.one_of(
    st.sampled_from(_KNOWN_REGIONS),
    st.text(alphabet=_SEGMENT_ALPHABET + "-", min_size=1, max_size=20),
)

# Distinctive, searchable secret values.
_secret_values = st.text(alphabet=_SEGMENT_ALPHABET, min_size=6, max_size=24).map(
    lambda body: _SECRET_MARKER + body
)

# Project root paths for the bind mount.
roots = st.text(alphabet=_SEGMENT_ALPHABET + "/", min_size=1, max_size=40).map(
    lambda p: "/" + p.strip("/")
)


@st.composite
def hyphenated_names(draw):
    """Generate realistic ``org-service-resource`` style hyphenated names."""
    parts = draw(st.lists(_segments, min_size=3, max_size=3))
    return "-".join(parts).lower()


@st.composite
def credentials(draw):
    """Generate a credentials dict keyed by the executor's env var names."""
    return {key: draw(_secret_values) for key in ENV_CRED_KEYS}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(hypenated_name, root="/project/root"):
    """Lightweight stand-in for a loaded Project (only .hypenated_name/.root used)."""
    return SimpleNamespace(hypenated_name=hypenated_name, root=root)


def _completed(args, returncode):
    return subprocess.CompletedProcess(
        args=["docker", *args],
        returncode=returncode,
        stdout=b"",
        stderr=b"" if returncode == 0 else b"boom",
    )


class _RecordingDocker:
    """A fake ``_run_docker`` that records calls and replays fixed results.

    ``pull_results`` queues one outcome per ``docker pull``: a ``returncode``
    int, or an exception instance to raise (modelling a timeout or a spawn
    failure). ``inspect_result`` is the outcome of the cached-image check, and
    ``run_returncode`` the container's exit code.

    Patched in as a plain instance rather than a function, so attribute lookup
    on the class does not bind ``self``.
    """

    def __init__(self, pull_results=(), inspect_result=1, run_returncode=0):
        self._pull_results = list(pull_results)
        self._inspect_result = inspect_result
        self._run_returncode = run_returncode
        self.calls = []

    def __call__(self, args, timeout=None, env=None, capture=True):
        self.calls.append(
            SimpleNamespace(args=list(args), timeout=timeout, env=env, capture=capture)
        )
        if args[0] == "pull":
            result = self._pull_results[len(self.pull_calls) - 1]
            if isinstance(result, BaseException):
                raise result
            return _completed(args, result)
        if args[:2] == ["image", "inspect"]:
            if isinstance(self._inspect_result, BaseException):
                raise self._inspect_result
            return _completed(args, self._inspect_result)
        return _completed(args, self._run_returncode)

    @property
    def pull_calls(self):
        return [call for call in self.calls if call.args[0] == "pull"]

    @property
    def run_calls(self):
        return [call for call in self.calls if call.args[0] == "run"]


def _patch_docker(fake):
    return mock.patch.object(RqtsImage, "_run_docker", fake)


# ===========================================================================
# Property 1: image resolution
# ===========================================================================
# Feature: cfn-test-v2-flag, Property 1: Image resolution honors override, else pinned default
@settings(max_examples=100)
@given(override=st.one_of(st.none(), st.just(""), image_refs))
def test_property_1_image_resolution_override_else_default(override):
    """The reference is the override when non-empty, else the pinned default.

    Validates: Requirements 2.1, 2.2
    """
    reference = RqtsImage(override).reference

    if override:
        assert reference == override
    else:
        assert reference == RQTS_IMAGE_REFERENCE


def test_no_reference_uses_default():
    """Constructed with no argument at all, the pinned default is used."""
    assert RqtsImage().reference == RQTS_IMAGE_REFERENCE


# ===========================================================================
# Property 2: bounded, anonymous pull
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
    least ``PULL_MAX_ATTEMPTS`` so ``ensure`` always has an outcome to consume
    even when every attempt fails.
    """
    outcome = st.one_of(
        st.just(0),
        st.integers(min_value=1, max_value=255),
        st.just(subprocess.TimeoutExpired(cmd="docker pull", timeout=1)),
        st.just(OSError("docker not found")),
    )
    return draw(
        st.lists(outcome, min_size=PULL_MAX_ATTEMPTS, max_size=PULL_MAX_ATTEMPTS + 4)
    )


# Feature: cfn-test-v2-flag, Property 2: Image pull is bounded and anonymous
@settings(max_examples=100)
@given(results=pull_result_sequences(), image_ref=image_refs, cached=st.booleans())
def test_property_2_pull_is_bounded_and_anonymous(results, image_ref, cached):
    """``ensure`` pulls at most PULL_MAX_ATTEMPTS regardless of the local cache
    state, stops on first success, never supplies AWS credentials to the pull,
    falls back to a cached image on exhaustion, and raises only when no cached
    copy exists.

    Validates: Requirements 2.3, 2.4, 2.5, 2.6
    """
    fake_docker = _RecordingDocker(results, inspect_result=0 if cached else 1)
    expected_attempts, should_succeed = _expected_attempts(results)

    # ``mock.patch`` context managers are used (rather than the monkeypatch
    # fixture) so the patches are applied and reset for every generated example.
    with _patch_docker(fake_docker):
        if should_succeed or cached:
            RqtsImage(image_ref).ensure()
        else:
            with pytest.raises(SysExitRecommendedError):
                RqtsImage(image_ref).ensure()

    # Bounded: pull is attempted at most PULL_MAX_ATTEMPTS times, and exactly the
    # number of attempts the retry policy predicts (stopping on first success).
    assert len(fake_docker.pull_calls) <= PULL_MAX_ATTEMPTS
    assert len(fake_docker.pull_calls) == expected_attempts

    for call in fake_docker.pull_calls:
        # Every invocation is an anonymous ``docker pull <ref>`` for this image.
        assert call.args == ["pull", image_ref]
        # The pull inherits the ambient environment: no credential is threaded
        # in, positionally or by keyword.
        assert call.env is None
        for token in call.args:
            for cred in _AWS_CRED_TOKENS:
                assert cred not in token


def test_pull_exhaustion_without_cached_image_raises():
    """All attempts fail with no cached image -> SysExitRecommendedError after
    exactly PULL_MAX_ATTEMPTS attempts.

    Validates: Requirements 2.6
    """
    fake_docker = _RecordingDocker([1] * (PULL_MAX_ATTEMPTS + 2), inspect_result=1)

    with _patch_docker(fake_docker):
        with pytest.raises(SysExitRecommendedError) as excinfo:
            RqtsImage("some/image:tag").ensure()

    assert len(fake_docker.pull_calls) == PULL_MAX_ATTEMPTS
    assert "some/image:tag" in str(excinfo.value)


def test_pull_exhaustion_with_cached_image_falls_back_with_warning(caplog):
    """All attempts fail but the image is cached locally -> warn and run from the
    local store instead of raising.

    Validates: Requirements 2.5
    """
    fake_docker = _RecordingDocker([1] * PULL_MAX_ATTEMPTS, inspect_result=0)

    with _patch_docker(fake_docker):
        with caplog.at_level("WARNING", logger=image_module.__name__):
            RqtsImage("cached/image:tag").ensure()

    assert len(fake_docker.pull_calls) == PULL_MAX_ATTEMPTS
    assert fake_docker.calls[-1].args == ["image", "inspect", "cached/image:tag"]
    assert any(
        "cached" in record.getMessage() and "cached/image:tag" in record.getMessage()
        for record in caplog.records
    )


def test_pull_exhaustion_on_repeated_timeouts():
    """Repeated per-attempt timeouts also exhaust after exactly PULL_MAX_ATTEMPTS."""
    timeouts = [
        subprocess.TimeoutExpired(cmd="docker pull", timeout=1)
        for _ in range(PULL_MAX_ATTEMPTS + 1)
    ]
    fake_docker = _RecordingDocker(timeouts, inspect_result=1)

    with _patch_docker(fake_docker):
        with pytest.raises(SysExitRecommendedError):
            RqtsImage("some/image:tag").ensure()

    assert len(fake_docker.pull_calls) == PULL_MAX_ATTEMPTS


def test_ensure_pulls_even_when_present_locally():
    """``ensure`` always attempts the pull, so a moved mutable tag (e.g. latest)
    is refreshed without a manual docker pull, and no inspect is needed on
    success.

    Validates: Requirements 2.3
    """
    fake_docker = _RecordingDocker([0], inspect_result=0)

    with _patch_docker(fake_docker):
        RqtsImage("present/image:tag").ensure()

    assert fake_docker.calls == [
        SimpleNamespace(
            args=["pull", "present/image:tag"],
            timeout=fake_docker.calls[0].timeout,
            env=None,
            capture=True,
        )
    ]
    # The per-attempt timeout is bounded so a hung pull cannot stall the run.
    assert fake_docker.pull_calls[0].timeout is not None


@pytest.mark.parametrize(
    "docker_error", [OSError("docker not found"), subprocess.SubprocessError("boom")]
)
def test_inspect_that_cannot_run_is_treated_as_absent(docker_error):
    """An inspect that cannot even run is treated as 'not cached'.

    Keeps the fallback decision safe when the docker CLI is missing or unusable:
    absent, rather than assumed cached.
    """
    fake_docker = _RecordingDocker([1] * PULL_MAX_ATTEMPTS, inspect_result=docker_error)

    with _patch_docker(fake_docker):
        with pytest.raises(SysExitRecommendedError):
            RqtsImage("ref:tag").ensure()


# ===========================================================================
# The docker seam
# ===========================================================================
def test_run_docker_invokes_docker_cli_with_fixed_argv():
    """``_run_docker`` drives the docker CLI with a fixed, non-shell argv.

    This is the one place that actually reaches ``subprocess.run``; it is
    patched here so no docker process is spawned. A fixed argv list (never a
    shell string) is what makes the image reference safe to pass through.
    """
    completed = subprocess.CompletedProcess(args=["docker", "info"], returncode=0)

    with mock.patch.object(
        image_module.subprocess, "run", return_value=completed
    ) as run:
        result = RqtsImage._run_docker(  # pylint: disable=protected-access
            ["image", "inspect", "ref:tag"], timeout=7
        )

    assert result is completed
    run.assert_called_once()
    assert run.call_args[0][0] == ["docker", "image", "inspect", "ref:tag"]
    assert run.call_args[1]["check"] is False
    assert run.call_args[1]["capture_output"] is True
    assert run.call_args[1]["timeout"] == 7
    # No env by default: the child inherits the ambient environment.
    assert run.call_args[1]["env"] is None


def test_run_docker_streams_when_capture_disabled():
    """``capture=False`` leaves stdout/stderr uncaptured so the child inherits
    the terminal and output streams live.

    Validates: Requirements 5.1
    """
    completed = subprocess.CompletedProcess(args=["docker", "run"], returncode=0)

    with mock.patch.object(
        image_module.subprocess, "run", return_value=completed
    ) as run:
        RqtsImage._run_docker(  # pylint: disable=protected-access
            ["run", "--rm", "img"], env={"A": "B"}, capture=False
        )

    assert run.call_args[1]["capture_output"] is False
    assert run.call_args[1]["env"] == {"A": "B"}


# ===========================================================================
# Property 4
# ===========================================================================
# Feature: cfn-test-v2-flag, Property 4: docker run bind-mounts the project root onto /work
@settings(max_examples=100)
@given(name=hyphenated_names(), region=regions, root=roots)
def test_property_4_docker_run_bind_mounts_project_root(name, region, root):
    args, _env = RqtsImage("img:ref").build_run_args(
        _make_project(name, root=root), region, CREDS
    )

    assert args[:2] == ["run", "--rm"]
    assert "-v" in args
    assert args[args.index("-v") + 1] == f"{root}:{CONTAINER_WORKDIR}"


# ===========================================================================
# Property 5
# ===========================================================================
def _env_entries(args):
    """Return the token following each ``-e`` flag."""
    return [args[i + 1] for i, token in enumerate(args) if token == "-e"]


# Feature: cfn-test-v2-flag, Property 5: credential values never enter the command
# line; they travel only through the returned env mapping
@settings(max_examples=100)
@given(name=hyphenated_names(), region=regions, creds=credentials())
def test_property_5_credentials_only_in_env_never_in_args(name, region, creds):
    args, env = RqtsImage("img:ref").build_run_args(_make_project(name), region, creds)

    # The -e flags are NAME-ONLY: the variable names are referenced so docker
    # inherits them from the client process environment; no `=` and no values.
    assert _env_entries(args) == list(ENV_CRED_KEYS) + list(CALLER_ENV_CRED_KEYS)

    # No credential secret value appears ANYWHERE in the arguments (this is what
    # makes the logged command line and `ps` output safe).
    for token in args:
        for secret in creds.values():
            assert secret not in token

    # The same credentials are exported under both name sets: the ambient SDK
    # chain reads AWS_*, and the executor repackages CALLER_AWS_* into the
    # handler request payload.
    for key, caller_key in zip(ENV_CRED_KEYS, CALLER_ENV_CRED_KEYS):
        assert env[key] == creds[key]
        assert env[caller_key] == creds[key]

    # The region reaches the executor through -r only, never as AWS_REGION.
    assert "AWS_REGION" not in env


# ===========================================================================
# Property 6
# ===========================================================================
# Feature: cfn-test-v2-flag, Property 6: run-tests receives the positional artifact path inside the mount
@settings(max_examples=100)
@given(name=hyphenated_names(), region=regions)
def test_property_6_extension_run_tests_and_artifact_path(name, region):
    args, _env = RqtsImage("img:ref").build_run_args(_make_project(name), region, CREDS)

    # The top-level extension selector precedes the run-tests subcommand.
    assert "--extension" in args
    ext_index = args.index("--extension")
    assert args[ext_index + 1] == EXTENSION_CONTRACT_TESTS
    assert args[ext_index + 2] == "run-tests"

    # The positional artifact path immediately follows run-tests and is addressed
    # under the container working directory.
    artifact_path = args[ext_index + 3]
    assert artifact_path == f"{CONTAINER_WORKDIR}/{name}.zip"


# ===========================================================================
# Property 7
# ===========================================================================
# Feature: cfn-test-v2-flag, Property 7: DirectJar handler mode is always selected
@settings(max_examples=100)
@given(name=hyphenated_names(), region=regions)
def test_property_7_direct_jar_mode_always_present(name, region):
    args, _env = RqtsImage("img:ref").build_run_args(_make_project(name), region, CREDS)

    assert args.count("--direct-jar") == 1


# ===========================================================================
# Property 8
# ===========================================================================
# Feature: cfn-test-v2-flag, Property 8: region argument always present with the effective region
@settings(max_examples=100)
@given(name=hyphenated_names(), use_default=st.booleans(), region=regions)
def test_property_8_region_argument_always_present(name, use_default, region):
    effective_region = CLI_DEFAULT_REGION if use_default else region
    args, _env = RqtsImage("img:ref").build_run_args(
        _make_project(name), effective_region, CREDS
    )

    assert "-r" in args
    assert args[args.index("-r") + 1] == effective_region


# ===========================================================================
# Property 9
# ===========================================================================
# Feature: cfn-test-v2-flag, Property 9: the old SAM Local / remote-lambda flags are never emitted
@settings(max_examples=100)
@given(name=hyphenated_names(), region=regions)
def test_property_9_forbidden_flags_never_emitted(name, region):
    args, _env = RqtsImage("img:ref").build_run_args(_make_project(name), region, CREDS)

    for flag in FORBIDDEN_FLAGS:
        assert flag not in args


# ===========================================================================
# Property 10
# ===========================================================================
# Feature: cfn-test-v2-flag, Property 10: no host networking is configured (DirectJar needs none)
@settings(max_examples=100)
@given(name=hyphenated_names(), region=regions)
def test_property_10_no_host_networking(name, region):
    args, _env = RqtsImage("img:ref").build_run_args(_make_project(name), region, CREDS)

    assert "--network" not in args
    assert "--add-host" not in args
    assert "host.docker.internal" not in " ".join(args)


# ===========================================================================
# Property 11
# ===========================================================================
# Feature: cfn-test-v2-flag, Property 11: output directory is emitted via -o under the mount
@settings(max_examples=100)
@given(name=hyphenated_names(), region=regions)
def test_property_11_output_dir_emitted(name, region):
    args, _env = RqtsImage("img:ref").build_run_args(_make_project(name), region, CREDS)

    assert "-o" in args
    assert args[args.index("-o") + 1] == CONTAINER_OUTPUT_DIR
    # The output dir lives under the container working directory mount.
    assert CONTAINER_OUTPUT_DIR.startswith(CONTAINER_WORKDIR)


# ===========================================================================
# Property 12
# ===========================================================================
# Feature: cfn-test-v2-flag, Property 12: no scenario-selection or exclusion flags
# are ever emitted; scenario selection is owned by the executor image
@settings(max_examples=100)
@given(name=hyphenated_names(), region=regions)
def test_property_12_no_scenario_selection_or_exclusion_flags(name, region):
    args, _env = RqtsImage("img:ref").build_run_args(_make_project(name), region, CREDS)

    assert "-s" not in args
    assert "--scenarios" not in args
    for token in args:
        assert not token.startswith("--exclude-")
    for tagging_scenario in FORBIDDEN_TAGGING_SCENARIOS:
        assert tagging_scenario not in args

    # The executor command therefore ends at the output directory.
    assert args[-2:] == ["-o", CONTAINER_OUTPUT_DIR]


# ===========================================================================
# Type configuration
# ===========================================================================
def test_type_configuration_referenced_by_name_and_valued_in_env():
    """A supplied type configuration is referenced by name in the arguments and
    its JSON content travels only in the env mapping."""
    type_configuration = json.dumps({"Credentials": {"ApiKey": f"{_SECRET_MARKER}key"}})

    args, env = RqtsImage("img:ref").build_run_args(
        _make_project("aws-foo-bar"),
        "us-east-1",
        CREDS,
        type_configuration=type_configuration,
    )

    assert ENV_TYPE_CONFIGURATION in _env_entries(args)
    assert env[ENV_TYPE_CONFIGURATION] == type_configuration
    for token in args:
        assert f"{_SECRET_MARKER}key" not in token


def test_type_configuration_omitted_leaves_variable_unset():
    """Without a type configuration the variable is neither referenced nor set,
    so the executor falls back to the one packaged in the artifact."""
    args, env = RqtsImage("img:ref").build_run_args(
        _make_project("aws-foo-bar"), "us-east-1", CREDS
    )

    assert ENV_TYPE_CONFIGURATION not in _env_entries(args)
    assert ENV_TYPE_CONFIGURATION not in env


def test_image_reference_precedes_the_executor_command():
    """The image is the last docker option and the executor command follows it."""
    args, _env = RqtsImage("img:ref").build_run_args(
        _make_project("aws-foo-bar", root="/my/project/root"), "us-east-1", CREDS
    )

    assert args[args.index("img:ref") + 1] == "--extension"
    assert args[args.index("-v") + 1] == f"/my/project/root:{CONTAINER_WORKDIR}"


# ===========================================================================
# Running the container
# ===========================================================================
def test_run_ensures_image_creates_output_dir_and_returns_exit_code(tmp_path):
    """``run`` pulls the image, creates the host output directory, spawns the
    container with the credential env merged over the ambient environment, and
    returns the container's exit code.
    """
    fake_docker = _RecordingDocker([0], run_returncode=0)
    project = _make_project("aws-foo-bar", root=str(tmp_path))

    with _patch_docker(fake_docker):
        with mock.patch.dict(image_module.os.environ, {"AMBIENT": "yes"}, clear=False):
            exit_code = RqtsImage("img:ref").run(project, "us-east-1", CREDS)

    assert exit_code == 0
    # The pull happened before the container ran.
    assert [call.args[0] for call in fake_docker.calls] == ["pull", "run"]
    # The host side of the bind-mounted output directory exists.
    assert (tmp_path / HOST_OUTPUT_DIRNAME).is_dir()

    run_call = fake_docker.run_calls[0]
    # Output streams live, and the ambient environment is preserved alongside
    # the credential values.
    assert run_call.capture is False
    assert run_call.env["AMBIENT"] == "yes"
    for key in ENV_CRED_KEYS + CALLER_ENV_CRED_KEYS:
        assert run_call.env[key] == CREDS[key.replace("CALLER_", "")]
    # No credential value appears in the arguments themselves.
    for token in run_call.args:
        assert token not in CREDS.values()


def test_run_returns_nonzero_container_exit_code(tmp_path):
    """A failing container's exit code is returned unchanged (no raise here)."""
    fake_docker = _RecordingDocker([0], run_returncode=7)

    with _patch_docker(fake_docker):
        exit_code = RqtsImage("img:ref").run(
            _make_project("aws-foo-bar", root=str(tmp_path)), "us-east-1", CREDS
        )

    assert exit_code == 7


def test_run_does_not_start_container_when_image_unavailable(tmp_path):
    """A fatal pull failure halts before the container is spawned."""
    fake_docker = _RecordingDocker([1] * PULL_MAX_ATTEMPTS, inspect_result=1)

    with _patch_docker(fake_docker):
        with pytest.raises(SysExitRecommendedError):
            RqtsImage("img:ref").run(
                _make_project("aws-foo-bar", root=str(tmp_path)), "us-east-1", CREDS
            )

    assert fake_docker.run_calls == []


@pytest.mark.parametrize(
    "spawn_error", [FileNotFoundError("no docker"), OSError("boom")]
)
def test_run_spawn_failure_raises(tmp_path, spawn_error):
    """A container that cannot be spawned surfaces as SysExitRecommendedError.

    Validates: Requirements 5.4
    """
    project = _make_project("aws-foo-bar", root=str(tmp_path))

    def docker(args, timeout=None, env=None, capture=True):
        # pylint: disable=unused-argument
        if args[0] == "pull":
            return _completed(args, 0)
        raise spawn_error

    # staticmethod: a plain function patched onto the class would bind ``self``.
    with _patch_docker(staticmethod(docker)):
        with pytest.raises(SysExitRecommendedError) as excinfo:
            RqtsImage("img:ref").run(project, "us-east-1", CREDS)

    assert "could not be started" in str(excinfo.value)


def test_run_passes_type_configuration_through_to_the_container(tmp_path):
    """The resolved type configuration reaches the container env, by name only in
    the arguments."""
    fake_docker = _RecordingDocker([0])
    type_configuration = json.dumps({"Credentials": {"ApiKey": "abc"}})

    with _patch_docker(fake_docker):
        RqtsImage("img:ref").run(
            _make_project("aws-foo-bar", root=str(tmp_path)),
            "us-east-1",
            CREDS,
            type_configuration=type_configuration,
        )

    run_call = fake_docker.run_calls[0]
    assert run_call.env[ENV_TYPE_CONFIGURATION] == type_configuration
    assert ENV_TYPE_CONFIGURATION in _env_entries(run_call.args)
