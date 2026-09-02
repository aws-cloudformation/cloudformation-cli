"""Tests for ``rpdk.core.rqts.runner``.

Covers the orchestration the runner still owns after everything Docker-facing
moved to :class:`rpdk.core.rqts.image.RqtsImage`: the artifact-type guards,
precondition aggregation, credential minting, type configuration resolution,
and the exit-code contract.

Docker and AWS are never invoked: ``RqtsImage`` and the ``boto_helpers``
functions imported into ``runner`` are patched at ``rpdk.core.rqts.runner``.

Library: Hypothesis (the standard Python property-based testing library). The
property test runs at least 100 generated examples via
``@settings(max_examples=100)`` and is tagged with a comment referencing the
design property it validates.
"""

import json
import logging
from types import SimpleNamespace
from unittest import mock

import pytest
from hypothesis import given, settings, strategies as st

from rpdk.core.contract.type_configuration import TypeConfiguration
from rpdk.core.exceptions import InvalidProjectError, SysExitRecommendedError
from rpdk.core.project import ARTIFACT_TYPE_HOOK, ARTIFACT_TYPE_RESOURCE
from rpdk.core.rqts.constants import ENV_CRED_KEYS, FAIL_MESSAGE, PASS_MESSAGE
from rpdk.core.rqts.runner import RqtsRunner

RUNNER_MODULE = "rpdk.core.rqts.runner"

CREDS = dict(zip(ENV_CRED_KEYS, ("AKID", "SECRET", "TOKEN")))


@pytest.fixture(autouse=True)
def _reset_type_configuration():
    """Keep the ``TypeConfiguration`` class-level cache from leaking between tests.

    The cache has no invalidation, so a value parsed by one test would otherwise
    be reused by the next.
    """
    TypeConfiguration.TYPE_CONFIGURATION = None
    yield
    TypeConfiguration.TYPE_CONFIGURATION = None


def _make_resource_project(root):
    """Build a minimal resource project the happy-path runner can drive."""
    return SimpleNamespace(
        artifact_type=ARTIFACT_TYPE_RESOURCE,
        type_name="AWS::Foo::Bar",
        hypenated_name="aws-foo-bar",
        root=root,
    )


def _make_args(**overrides):
    args = SimpleNamespace(
        region="us-east-1",
        profile=None,
        role_arn=None,
        source_account=None,
        source_arn=None,
        typeconfig=None,
        rqts_image=None,
    )
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


class _Pipeline:
    """Context manager patching everything ``RqtsRunner.run`` depends on."""

    def __init__(self, exit_code=0, type_configuration=None, failures=()):
        self._exit_code = exit_code
        self._patches = {
            "check": mock.patch(
                f"{RUNNER_MODULE}.check_preconditions", return_value=list(failures)
            ),
            "session": mock.patch(f"{RUNNER_MODULE}.create_sdk_session"),
            "creds": mock.patch(
                f"{RUNNER_MODULE}.get_temporary_credentials", return_value=CREDS
            ),
            "typeconfig": mock.patch.object(
                TypeConfiguration,
                "get_type_configuration",
                return_value=type_configuration,
            ),
            "image": mock.patch(f"{RUNNER_MODULE}.RqtsImage", autospec=True),
        }
        self.mocks = {}

    def __enter__(self):
        self.mocks = {name: patch.start() for name, patch in self._patches.items()}
        self.image.return_value.run.return_value = self._exit_code
        return self

    def __exit__(self, *_exc):
        for patch in reversed(list(self._patches.values())):
            patch.stop()
        return False

    @property
    def image(self):
        return self.mocks["image"]

    @property
    def container_run(self):
        """The mocked ``RqtsImage.run`` the runner delegates to."""
        return self.mocks["image"].return_value.run

    @property
    def get_type_configuration(self):
        return self.mocks["typeconfig"]

    @property
    def get_temporary_credentials(self):
        return self.mocks["creds"]


# ===========================================================================
# Property 12: exit-code mapping
# ===========================================================================
# Feature: cfn-test-v2-flag, Property 12: Exit code mapping
@settings(max_examples=100, deadline=None)
@given(
    code=st.one_of(
        st.just(0),
        st.integers(min_value=1, max_value=255),
        st.integers(min_value=-255, max_value=-1),
        st.integers(),
    )
)
def test_property_12_exit_code_mapping(code):
    """A zero container exit code returns normally; any non-zero code raises
    SysExitRecommendedError with the fail message.

    Validates: Requirements 5.2, 5.3, 6.3
    """
    TypeConfiguration.TYPE_CONFIGURATION = None
    runner = RqtsRunner(_make_args(), _make_resource_project("/tmp/project"))

    with _Pipeline(exit_code=code):
        if code == 0:
            assert runner.run() is None
        else:
            with pytest.raises(SysExitRecommendedError) as excinfo:
                runner.run()
            assert str(excinfo.value) == FAIL_MESSAGE


# ===========================================================================
# Artifact-type guards
# ===========================================================================
def test_guard_artifact_type_hook_rejected_and_does_not_proceed():
    """Hook project -> SysExitRecommendedError 'resources only'; pipeline halts.

    Validates: Requirements 7.2
    """
    runner = RqtsRunner(_make_args(), SimpleNamespace(artifact_type=ARTIFACT_TYPE_HOOK))

    with mock.patch(f"{RUNNER_MODULE}.check_preconditions") as check, mock.patch(
        f"{RUNNER_MODULE}.RqtsImage"
    ) as image:
        with pytest.raises(SysExitRecommendedError) as excinfo:
            runner.run()

    assert "resource types only" in str(excinfo.value)
    # The guard fails fast: no downstream stage runs.
    check.assert_not_called()
    image.assert_not_called()


def test_guard_artifact_type_indeterminate_rejected_and_does_not_proceed():
    """Indeterminate artifact type -> 'could not determine' error; pipeline halts.

    Validates: Requirements 7.5
    """
    runner = RqtsRunner(_make_args(), SimpleNamespace(artifact_type=None))

    with mock.patch(f"{RUNNER_MODULE}.check_preconditions") as check, mock.patch(
        f"{RUNNER_MODULE}.RqtsImage"
    ) as image:
        with pytest.raises(SysExitRecommendedError) as excinfo:
            runner.run()

    assert "could not determine the project artifact type" in str(excinfo.value)
    check.assert_not_called()
    image.assert_not_called()


# ===========================================================================
# Precondition enforcement
# ===========================================================================
def test_run_unmet_preconditions_aggregated_and_halts():
    """Unmet preconditions -> a single error naming every failure; nothing runs.

    The runner turns the aggregated list from ``check_preconditions`` into one
    ``SysExitRecommendedError`` instead of failing on the first problem, and
    halts before any container is started.

    Validates: Requirements 3.1, 3.5, 3.7
    """
    runner = RqtsRunner(_make_args(), _make_resource_project("/tmp/project"))
    failures = [
        "Docker is required and must be running: the Docker daemon could not "
        "be reached.",
        "artifact package 'aws-foo-bar.zip' not found; build the project first.",
    ]

    with _Pipeline(failures=failures) as pipeline:
        with pytest.raises(SysExitRecommendedError) as excinfo:
            runner.run()

    message = str(excinfo.value)
    assert "preconditions were not met" in message
    for failure in failures:
        assert failure in message
    pipeline.image.assert_not_called()


# ===========================================================================
# Credentials and type configuration
# ===========================================================================
def test_run_mints_credentials_keyed_for_the_executor():
    """Credentials are requested with the executor's env var names as key names,
    with the confused-deputy headers, and handed to the image unchanged.

    Validates: Requirements 3.5
    """
    args = _make_args(
        role_arn="arn:aws:iam::1:role/r", source_account="1", source_arn="arn:x"
    )
    project = _make_resource_project("/tmp/project")
    runner = RqtsRunner(args, project)

    with _Pipeline() as pipeline:
        runner.run()

    session = pipeline.get_temporary_credentials.call_args[0][0]
    assert pipeline.get_temporary_credentials.call_args[0][1] is ENV_CRED_KEYS
    assert pipeline.get_temporary_credentials.call_args[0][2] == args.role_arn
    assert pipeline.get_temporary_credentials.call_args[1]["headers"] == {
        "account_id": "1",
        "source_arn": "arn:x",
    }
    assert session is not None

    pipeline.image.assert_called_once_with(args.rqts_image)
    pipeline.container_run.assert_called_once_with(
        project, args.region, CREDS, type_configuration=None
    )


def test_run_serializes_type_configuration_to_json():
    """A resolved type configuration is passed to the image as a JSON string."""
    config = {"Credentials": {"ApiKey": "123", "ApplicationKey": "456"}}
    project = _make_resource_project("/tmp/project")
    runner = RqtsRunner(_make_args(typeconfig="./tc.json"), project)

    with _Pipeline(type_configuration=config) as pipeline:
        runner.run()

    pipeline.get_type_configuration.assert_called_once_with("./tc.json")
    passed = pipeline.container_run.call_args[1]["type_configuration"]
    assert json.loads(passed) == config


@pytest.mark.parametrize("config", [None, {}])
def test_run_passes_no_type_configuration_when_absent_or_empty(config):
    """A missing or empty type configuration leaves the variable unset so the
    executor falls back to the one packaged in the artifact."""
    runner = RqtsRunner(_make_args(), _make_resource_project("/tmp/project"))

    with _Pipeline(type_configuration=config) as pipeline:
        runner.run()

    assert pipeline.container_run.call_args[1]["type_configuration"] is None


def test_run_clears_the_type_configuration_cache_before_reading():
    """The class-level cache is cleared so each run reads the file from disk
    rather than reusing a value parsed earlier in the process."""
    TypeConfiguration.TYPE_CONFIGURATION = {"stale": True}
    observed = {}

    def record(typeconfigloc):  # pylint: disable=unused-argument
        observed["cache"] = TypeConfiguration.TYPE_CONFIGURATION

    runner = RqtsRunner(_make_args(), _make_resource_project("/tmp/project"))

    with _Pipeline() as pipeline:
        pipeline.get_type_configuration.side_effect = record
        runner.run()

    assert observed["cache"] is None


def test_run_surfaces_invalid_type_configuration():
    """An invalid type configuration file fails the run with the CLI's own
    InvalidProjectError (a SysExitRecommendedError), before the container runs."""
    runner = RqtsRunner(
        _make_args(typeconfig="./bad.json"), _make_resource_project("/x")
    )

    with _Pipeline() as pipeline:
        pipeline.get_type_configuration.side_effect = InvalidProjectError(
            "Type configuration file './bad.json' is invalid"
        )
        with pytest.raises(SysExitRecommendedError) as excinfo:
            runner.run()

    assert "is invalid" in str(excinfo.value)
    pipeline.container_run.assert_not_called()


# ===========================================================================
# Reporting
# ===========================================================================
def test_run_logs_pass_message_on_success(caplog):
    """A passing run logs the pass message at INFO and returns.

    Validates: Requirements 6.1
    """
    runner = RqtsRunner(_make_args(), _make_resource_project("/tmp/project"))

    with _Pipeline(exit_code=0):
        with caplog.at_level(logging.INFO, logger=RUNNER_MODULE):
            assert runner.run() is None

    assert PASS_MESSAGE in caplog.text
