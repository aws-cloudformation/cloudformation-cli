"""Tests for ``rpdk.core.rqts.preconditions``.

Covers:
- Property 3: precondition failures are aggregated exactly (over the three
  DirectJar checks: Docker runtime, artifact package, credentials+region).
- Each precondition failing in isolation produces its own message and prevents
  any container run.

The DirectJar handler mode has no SAM Local endpoint to probe and reads inputs
from the packaged artifact zip, so there is no endpoint or inputs check.

Every check is controlled independently by patching within
``rpdk.core.rqts.preconditions`` (``shutil.which`` + ``subprocess.run`` for
Docker, ``create_sdk_session`` for credentials) and by toggling the artifact
package file under a ``tmp_path`` working directory.
"""

import contextlib
import subprocess
from unittest import mock

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from rpdk.core.exceptions import CLIMisconfiguredError
from rpdk.core.rqts.preconditions import check_preconditions

PRECONDITIONS_MODULE = "rpdk.core.rqts.preconditions"

# The three checks, in the order check_preconditions runs them, keyed to the
# distinctive substring of the failure message each one emits.
CHECK_NAMES = ("docker", "artifact", "credentials")
MESSAGE_SUBSTRINGS = {
    "docker": "Docker is required",
    "artifact": "artifact package",
    "credentials": "valid AWS credentials and a region",
}


class FakeProject:
    """Minimal stand-in for ``rpdk.core.project.Project``.

    Only the attributes the precondition checks read are provided: ``root`` and
    ``hypenated_name``.
    """

    def __init__(self, root):
        self.root = root
        self.hypenated_name = "aws-foo-bar"


def _make_args():
    args = mock.Mock()
    args.region = "us-east-1"
    args.profile = None
    return args


@contextlib.contextmanager
def configured_env(work_dir, states):
    """Force each precondition to pass/fail per ``states``.

    ``states`` maps check name -> bool, where ``True`` means the check should
    PASS and ``False`` means it should FAIL. Yields ``(args, project)`` wired so
    that ``check_preconditions`` observes exactly those outcomes.
    """
    project = FakeProject(work_dir)

    # Artifact package presence (real filesystem toggle).
    artifact_path = work_dir / f"{project.hypenated_name}.zip"
    if states["artifact"]:
        artifact_path.write_bytes(b"zip")
    elif artifact_path.exists():
        artifact_path.unlink()

    # Docker: which() present + `docker info` returncode 0 => pass.
    which_return = "/usr/bin/docker" if states["docker"] else None
    docker_info_result = mock.Mock(returncode=0 if states["docker"] else 1)

    # Credentials: create_sdk_session succeeds => pass, raises => fail.
    session_side_effect = (
        None if states["credentials"] else CLIMisconfiguredError("no creds")
    )

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            mock.patch(
                f"{PRECONDITIONS_MODULE}.shutil.which", return_value=which_return
            )
        )
        stack.enter_context(
            mock.patch(
                f"{PRECONDITIONS_MODULE}.subprocess.run",
                return_value=docker_info_result,
            )
        )
        stack.enter_context(
            mock.patch(
                f"{PRECONDITIONS_MODULE}.create_sdk_session",
                return_value=mock.Mock(),
                side_effect=session_side_effect,
            )
        )
        yield _make_args(), project


def _matched_checks(failures):
    """Return the set of check names whose message substring appears in ``failures``."""
    matched = set()
    for name, substring in MESSAGE_SUBSTRINGS.items():
        if any(substring in message for message in failures):
            matched.add(name)
    return matched


# Feature: cfn-test-v2-flag, Property 3: For any subset of the precondition
# checks (Docker runtime, artifact package, credentials+region) forced to fail,
# check_preconditions returns a failure list whose messages correspond to
# exactly that subset - every unmet precondition is named and every met
# precondition is absent.
@settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(pass_flags=st.fixed_dictionaries({name: st.booleans() for name in CHECK_NAMES}))
def test_precondition_failures_aggregated_exactly(tmp_path, pass_flags):
    """Validates: Requirements 3.7"""
    expected_failures = {name for name, passed in pass_flags.items() if not passed}

    with configured_env(tmp_path, pass_flags) as (args, project):
        failures = check_preconditions(args, project)

    # Every unmet precondition is named exactly once, and no met precondition is.
    assert _matched_checks(failures) == expected_failures
    assert len(failures) == len(expected_failures)


# ---------------------------------------------------------------------------
# Each precondition failing in isolation.
# ---------------------------------------------------------------------------

ALL_PASS = dict.fromkeys(CHECK_NAMES, True)


def _states_with_only_failing(check):
    states = dict(ALL_PASS)
    states[check] = False
    return states


def test_all_preconditions_met_returns_empty(tmp_path):
    """Sanity baseline: when every check passes, no failures are returned."""
    with configured_env(tmp_path, dict(ALL_PASS)) as (args, project):
        assert not check_preconditions(args, project)


def test_docker_unavailable_in_isolation(tmp_path):
    """Requirement 3.2: Docker unavailable yields its message and blocks the run."""
    with configured_env(tmp_path, _states_with_only_failing("docker")) as (
        args,
        project,
    ):
        failures = check_preconditions(args, project)

    assert len(failures) == 1
    assert MESSAGE_SUBSTRINGS["docker"] in failures[0]
    # A non-empty failure list prevents the caller from ever running a container.
    assert failures


def test_artifact_missing_in_isolation(tmp_path):
    """Requirement 3.3: missing artifact package yields its message and blocks the run."""
    with configured_env(tmp_path, _states_with_only_failing("artifact")) as (
        args,
        project,
    ):
        failures = check_preconditions(args, project)

    assert len(failures) == 1
    assert MESSAGE_SUBSTRINGS["artifact"] in failures[0]
    assert failures


def test_credentials_unavailable_in_isolation(tmp_path):
    """Requirement 3.5: missing credentials/region yields the message and blocks the run."""
    with configured_env(tmp_path, _states_with_only_failing("credentials")) as (
        args,
        project,
    ):
        failures = check_preconditions(args, project)

    assert len(failures) == 1
    assert MESSAGE_SUBSTRINGS["credentials"] in failures[0]
    assert failures


# ---------------------------------------------------------------------------
# Docker daemon ping failure modes (docker CLI present, daemon unreachable).
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def docker_ping_env(work_dir, **run_kwargs):
    """Yield ``(args, project)`` with docker on PATH and ``docker info`` stubbed.

    The artifact and credential checks are forced to pass, so any failure the
    caller observes comes from the Docker daemon ping alone. ``run_kwargs`` is
    forwarded to ``mock.patch`` for ``subprocess.run`` (``return_value`` for an
    exit status, ``side_effect`` to raise).
    """
    project = FakeProject(work_dir)
    (work_dir / f"{project.hypenated_name}.zip").write_bytes(b"zip")

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            mock.patch(
                f"{PRECONDITIONS_MODULE}.shutil.which", return_value="/usr/bin/docker"
            )
        )
        stack.enter_context(
            mock.patch(f"{PRECONDITIONS_MODULE}.subprocess.run", **run_kwargs)
        )
        stack.enter_context(
            mock.patch(
                f"{PRECONDITIONS_MODULE}.create_sdk_session", return_value=mock.Mock()
            )
        )
        yield _make_args(), project


def test_docker_daemon_ping_nonzero_exit_reports_unreachable(tmp_path):
    """docker CLI present but ``docker info`` exits non-zero -> unreachable daemon.

    Distinct from the missing-CLI case: the binary exists, so the ping itself is
    what fails.

    Validates: Requirements 3.2
    """
    with docker_ping_env(tmp_path, return_value=mock.Mock(returncode=1)) as (
        args,
        project,
    ):
        failures = check_preconditions(args, project)

    assert len(failures) == 1
    assert MESSAGE_SUBSTRINGS["docker"] in failures[0]


@pytest.mark.parametrize(
    "ping_error",
    [OSError("cannot exec"), subprocess.TimeoutExpired(cmd="docker info", timeout=10)],
)
def test_docker_daemon_ping_error_reports_unreachable(tmp_path, ping_error):
    """A ping that raises (spawn failure or timeout) -> unreachable daemon.

    The check converts the exception into a message rather than propagating it,
    so a hung or broken daemon still aggregates with other failures.

    Validates: Requirements 3.2
    """
    with docker_ping_env(tmp_path, side_effect=ping_error) as (args, project):
        failures = check_preconditions(args, project)

    assert len(failures) == 1
    assert MESSAGE_SUBSTRINGS["docker"] in failures[0]
