"""Tests for ``rpdk.core.rqts.runner``.

Covers:
- Property 12: exit-code mapping (``map_exit_code``) over arbitrary exit codes.
- Orchestration guards and container spawn failure edge cases
  (``run_container`` spawn failure, ``RqtsRunner._guard_artifact_type`` for hook
  and indeterminate artifact types).
- Live output streaming integration for ``run_container`` using a fake child
  process (no real Docker).
- Result reporting (``report_result``) pass/fail summaries and the
  ``RqtsRunner.run`` DEBUG log of the full ``docker run`` command line.

Docker and AWS are never actually invoked: ``subprocess.Popen`` is patched with
a deterministic fake, and the sibling functions imported into ``runner`` are
patched at ``rpdk.core.rqts.runner`` so the happy path exercises the
orchestration wiring without any external calls.

Library: Hypothesis (the standard Python property-based testing library). The
property test runs at least 100 generated examples via
``@settings(max_examples=100)`` and is tagged with a comment referencing the
design property it validates.
"""
import logging
from types import SimpleNamespace
from unittest import mock

import pytest
from hypothesis import given, settings, strategies as st

from rpdk.core.exceptions import SysExitRecommendedError
from rpdk.core.project import ARTIFACT_TYPE_HOOK, ARTIFACT_TYPE_RESOURCE
from rpdk.core.rqts.runner import (
    FAIL_SUMMARY,
    PASS_SUMMARY,
    RqtsRunner,
    map_exit_code,
    report_result,
    run_container,
)

RUNNER_MODULE = "rpdk.core.rqts.runner"


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakePopen:
    """Deterministic stand-in for ``subprocess.Popen``.

    Supports the context-manager protocol used by ``run_container`` and records
    that ``wait()`` was called before the return code is surfaced, so the test
    can assert the child was awaited (i.e. streamed to completion) rather than
    abandoned. Optionally emits incremental "live" output lines to a sink to
    model streaming.
    """

    def __init__(self, argv, return_code=0, output_lines=None, output_sink=None):
        self.argv = argv
        self._return_code = return_code
        self._output_lines = list(output_lines or [])
        self._output_sink = output_sink
        self.waited = False
        self.entered = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *_exc):
        return False

    def wait(self):
        # Model live streaming: output is surfaced as the process runs, before
        # wait() returns the exit code.
        if self._output_sink is not None:
            for line in self._output_lines:
                self._output_sink.append(line)
        self.waited = True
        return self._return_code


def _make_resource_project(root):
    """Build a minimal resource project the happy-path runner can drive."""
    return SimpleNamespace(
        artifact_type=ARTIFACT_TYPE_RESOURCE,
        type_name="AWS::Foo::Bar",
        hypenated_name="aws-foo-bar",
        root=root,
    )


def _make_args():
    return SimpleNamespace(
        region="us-east-1",
        profile=None,
        role_arn=None,
        source_account=None,
        source_arn=None,
        rqts_image=None,
    )


# ===========================================================================
# Property 12: exit-code mapping
# ===========================================================================
# Feature: cfn-test-v2-flag, Property 12: Exit code mapping
@settings(max_examples=100)
@given(
    code=st.one_of(
        st.just(0),
        st.integers(min_value=1, max_value=255),
        st.integers(min_value=-255, max_value=-1),
        st.integers(),
    )
)
def test_property_12_exit_code_mapping(code):
    """map_exit_code(0) returns None without raising; any non-zero code raises
    SysExitRecommendedError.

    Validates: Requirements 5.2, 5.3, 6.3
    """
    if code == 0:
        assert map_exit_code(code) is None
    else:
        with pytest.raises(SysExitRecommendedError):
            map_exit_code(code)


# ===========================================================================
# Orchestration guards and spawn failure
# ===========================================================================
@pytest.mark.parametrize(
    "spawn_error", [FileNotFoundError("no docker"), OSError("boom")]
)
def test_run_container_spawn_failure_raises(spawn_error):
    """Container spawn failure -> SysExitRecommendedError naming the start failure.

    Validates: Requirements 5.4
    """
    with mock.patch(f"{RUNNER_MODULE}.subprocess.Popen", side_effect=spawn_error):
        with pytest.raises(SysExitRecommendedError) as excinfo:
            run_container(["docker", "run", "--rm", "image"])

    assert "could not be started" in str(excinfo.value)


def test_guard_artifact_type_hook_rejected_and_does_not_proceed():
    """Hook project -> SysExitRecommendedError 'resources only'; pipeline halts.

    Validates: Requirements 7.2
    """
    project = SimpleNamespace(artifact_type=ARTIFACT_TYPE_HOOK)
    rqts_runner = RqtsRunner(_make_args(), project)

    with mock.patch(f"{RUNNER_MODULE}.check_preconditions") as check, mock.patch(
        f"{RUNNER_MODULE}.run_container"
    ) as run:
        with pytest.raises(SysExitRecommendedError) as excinfo:
            rqts_runner.run()

    assert "resource types only" in str(excinfo.value)
    # The guard fails fast: no downstream stage runs.
    check.assert_not_called()
    run.assert_not_called()


def test_guard_artifact_type_indeterminate_rejected_and_does_not_proceed():
    """Indeterminate artifact type -> 'could not determine' error; pipeline halts.

    Validates: Requirements 7.5
    """
    project = SimpleNamespace(artifact_type=None)
    rqts_runner = RqtsRunner(_make_args(), project)

    with mock.patch(f"{RUNNER_MODULE}.check_preconditions") as check, mock.patch(
        f"{RUNNER_MODULE}.run_container"
    ) as run:
        with pytest.raises(SysExitRecommendedError) as excinfo:
            rqts_runner.run()

    assert "could not determine the project artifact type" in str(excinfo.value)
    check.assert_not_called()
    run.assert_not_called()


# ===========================================================================
# Live output streaming integration
# ===========================================================================
def test_run_container_streams_output_and_returns_code():
    """run_container surfaces incremental child output and returns the exit code.

    A fake child process emits incremental lines as it runs (before wait()
    returns), modelling the inherited-stdio live streaming; run_container
    returns the child's exit code.

    Validates: Requirements 5.1
    """
    argv = [
        "docker",
        "run",
        "--rm",
        "image:tag",
        "--extension",
        "contract-tests",
        "run-tests",
        "/work/aws-foo-bar.zip",
        "--direct-jar",
    ]
    streamed = []
    process = FakePopen(
        argv,
        return_code=0,
        output_lines=["scenario create: PASS", "scenario delete: PASS"],
        output_sink=streamed,
    )

    def factory(passed_argv, *_args, **_kwargs):
        # run_container must spawn docker with exactly the argv it was given.
        assert passed_argv == argv
        return process

    with mock.patch(f"{RUNNER_MODULE}.subprocess.Popen", side_effect=factory):
        code = run_container(argv)

    assert code == 0
    # Output was surfaced live (during the run) and the child was awaited.
    assert streamed == ["scenario create: PASS", "scenario delete: PASS"]
    assert process.waited is True


def test_run_container_returns_nonzero_code():
    """run_container returns a non-zero child exit code unchanged (no raise)."""
    argv = ["docker", "run", "--rm", "image:tag"]

    with mock.patch(
        f"{RUNNER_MODULE}.subprocess.Popen",
        side_effect=lambda passed_argv, *a, **k: FakePopen(passed_argv, return_code=7),
    ):
        assert run_container(argv) == 7


def test_run_container_merges_env_over_ambient_environment(monkeypatch):
    """run_container spawns docker with the supplied env merged over os.environ,
    and inherits the ambient environment untouched (env=None) when none is given.

    This is the delivery half of the name-only ``-e`` contract: credential
    values reach docker exclusively through the process environment.
    """
    argv = ["docker", "run", "--rm", "image:tag"]
    captured = {}

    def factory(passed_argv, *_args, **kwargs):
        captured["env"] = kwargs.get("env")
        return FakePopen(passed_argv, return_code=0)

    monkeypatch.setenv("SOME_AMBIENT_VAR", "ambient")

    with mock.patch(f"{RUNNER_MODULE}.subprocess.Popen", side_effect=factory):
        run_container(argv, env={"AWS_ACCESS_KEY_ID": "AKID"})
    assert captured["env"]["AWS_ACCESS_KEY_ID"] == "AKID"
    assert captured["env"]["SOME_AMBIENT_VAR"] == "ambient"

    with mock.patch(f"{RUNNER_MODULE}.subprocess.Popen", side_effect=factory):
        run_container(argv)
    assert captured["env"] is None


# ===========================================================================
# Result reporting and DEBUG logging
# ===========================================================================
def test_report_result_pass_logs_summary_and_does_not_raise(caplog):
    """report_result(0) logs PASS_SUMMARY at INFO and does not raise.

    Validates: Requirements 6.1
    """
    with caplog.at_level(logging.INFO, logger=RUNNER_MODULE):
        assert report_result(0) is None

    assert PASS_SUMMARY in caplog.text


def test_report_result_fail_raises_with_fail_summary():
    """report_result(non-zero) raises SysExitRecommendedError with FAIL_SUMMARY.

    Validates: Requirements 6.2
    """
    with pytest.raises(SysExitRecommendedError) as excinfo:
        report_result(1)

    assert str(excinfo.value) == FAIL_SUMMARY


def test_run_logs_full_docker_command_at_debug_on_happy_path(tmp_path, caplog):
    """RqtsRunner.run logs the full docker run command at DEBUG and passes.

    A fully-mocked happy path (no preconditions failures, stubbed credentials,
    image resolve/ensure, and a zero container exit code) drives the runner and
    asserts the full docker command line is emitted at DEBUG and the run reports
    a pass. It also asserts check_preconditions is called with (args, project).

    Validates: Requirements 4.10, 6.1
    """
    project = _make_resource_project(str(tmp_path))
    args = _make_args()
    rqts_runner = RqtsRunner(args, project)
    docker_argv = [
        "docker",
        "run",
        "--rm",
        "image:tag",
        "--extension",
        "contract-tests",
        "run-tests",
        "/work/aws-foo-bar.zip",
        "--direct-jar",
    ]

    creds = {
        "aws_access_key_id": "AKID",
        "aws_secret_access_key": "SECRET",
        "aws_session_token": "TOKEN",
    }

    with mock.patch(
        f"{RUNNER_MODULE}.check_preconditions", return_value=[]
    ) as check, mock.patch(f"{RUNNER_MODULE}.create_sdk_session"), mock.patch(
        f"{RUNNER_MODULE}.get_temporary_credentials", return_value=creds
    ), mock.patch(
        f"{RUNNER_MODULE}.resolve_image", return_value="image:tag"
    ), mock.patch(
        f"{RUNNER_MODULE}.ensure_image"
    ), mock.patch(
        f"{RUNNER_MODULE}.build_docker_argv", return_value=docker_argv
    ), mock.patch(
        f"{RUNNER_MODULE}.run_container", return_value=0
    ) as run:
        with caplog.at_level(logging.DEBUG, logger=RUNNER_MODULE):
            # Returns normally (pass) on a zero container exit code.
            assert rqts_runner.run() is None

    # check_preconditions is called with exactly (args, project) - no host arg.
    check.assert_called_once_with(args, project)
    # run_container receives the credential-free argv plus the env mapping that
    # carries the credential values (never present in the argv itself).
    run.assert_called_once_with(
        docker_argv,
        env={
            "AWS_ACCESS_KEY_ID": "AKID",
            "AWS_SECRET_ACCESS_KEY": "SECRET",
            "AWS_SESSION_TOKEN": "TOKEN",
            "AWS_REGION": args.region,
        },
    )
    # The DEBUG-logged command line contains no credential values.
    for record in caplog.records:
        for secret in creds.values():
            assert secret not in record.getMessage()
    # The host-side output directory was created under the project root.
    assert (tmp_path / "rqts-output").is_dir()
    # The full docker run command line is logged at DEBUG (Req 4.10).
    debug_records = [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.DEBUG
    ]
    joined_command = " ".join(docker_argv)
    assert any(joined_command in message for message in debug_records)
    # The pass summary is surfaced (Req 6.1).
    assert PASS_SUMMARY in caplog.text


# ===========================================================================
# Precondition enforcement inside the pipeline
# ===========================================================================
def test_run_unmet_preconditions_aggregated_and_halts(tmp_path):
    """Unmet preconditions -> a single error naming every failure; nothing runs.

    The runner turns the aggregated list from ``check_preconditions`` into one
    ``SysExitRecommendedError`` instead of failing on the first problem, and
    halts before the image is ensured or any container is started.

    Validates: Requirements 3.1, 3.5
    """
    project = _make_resource_project(str(tmp_path))
    rqts_runner = RqtsRunner(_make_args(), project)
    failures = [
        "Docker is required and must be running: the Docker daemon could not "
        "be reached.",
        "artifact package 'aws-foo-bar.zip' not found; build the project first.",
    ]

    with mock.patch(
        f"{RUNNER_MODULE}.check_preconditions", return_value=failures
    ), mock.patch(f"{RUNNER_MODULE}.ensure_image") as ensure, mock.patch(
        f"{RUNNER_MODULE}.run_container"
    ) as run:
        with pytest.raises(SysExitRecommendedError) as excinfo:
            rqts_runner.run()

    message = str(excinfo.value)
    assert "preconditions were not met" in message
    for failure in failures:
        assert failure in message
    ensure.assert_not_called()
    run.assert_not_called()
