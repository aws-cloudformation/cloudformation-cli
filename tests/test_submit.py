# Tests for rpdk.core.submit (the ``cfn submit`` sub-command).
#
# pylint: disable=protected-access,redefined-outer-name
"""Unit tests for :mod:`rpdk.core.submit`, covering both the classic
packaging workflow and the ``--package`` (pre-built zip) workflow added
by the submit-existing-zip feature.
"""
import argparse
import json
import zipfile
from pathlib import Path
from unittest.mock import ANY, patch

import pytest

from rpdk.core.exceptions import InvalidProjectError
from rpdk.core.package_validator import (
    ARTIFACT_TYPE_HOOK,
    ARTIFACT_TYPE_MODULE,
    ARTIFACT_TYPE_RESOURCE,
    SCHEMA_FILENAME,
    SETTINGS_FILENAME,
)
from rpdk.core.submit import (
    _submit_existing_package,
    _validate_package_flag_combinations,
    setup_subparser,
    submit,
)

# ---------------------------------------------------------------------------
# Helpers and fixtures
# ---------------------------------------------------------------------------


def _build_submit_parser():
    root = argparse.ArgumentParser()
    subs = root.add_subparsers(dest="command")
    setup_subparser(subs, [])
    return root


@pytest.fixture
def submit_parser():
    return _build_submit_parser()


def _make_valid_zip(
    path: Path, artifact_type=ARTIFACT_TYPE_RESOURCE, type_name="Acme::Example::Widget"
) -> Path:
    with zipfile.ZipFile(path, mode="w") as zf:
        zf.writestr(
            SETTINGS_FILENAME,
            json.dumps({"typeName": type_name, "artifact_type": artifact_type}),
        )
        zf.writestr(SCHEMA_FILENAME, json.dumps({"typeName": type_name}))
    return path


def _default_args(**overrides):
    """argparse.Namespace matching what the real parser would produce."""
    base = {
        "package": None,
        "dry_run": False,
        "endpoint_url": None,
        "region": None,
        "profile": None,
        "role_arn": None,
        "use_role": True,
        "set_default": False,
        "use_docker": False,
        "no_docker": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def test_parser_accepts_package_long_form(submit_parser):
    args = submit_parser.parse_args(["submit", "--package", "foo.zip"])
    assert args.package == "foo.zip"


def test_parser_accepts_package_short_form(submit_parser):
    args = submit_parser.parse_args(["submit", "-p", "foo.zip"])
    assert args.package == "foo.zip"


def test_parser_defaults_package_to_none(submit_parser):
    args = submit_parser.parse_args(["submit"])
    assert args.package is None


def test_submit_help_mentions_package_option(submit_parser):
    submit_sub = submit_parser._subparsers._actions[-1].choices["submit"]
    help_text = submit_sub.format_help()
    assert "--package" in help_text
    assert "-p" in help_text
    assert "pre-built" in help_text
    # Restriction is explained in help so users can discover it.
    assert "--dry-run" in help_text
    assert "--use-docker" in help_text


# ---------------------------------------------------------------------------
# Flag combination validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "flag,expected_name",
    [
        ("dry_run", "--dry-run"),
        ("use_docker", "--use-docker"),
        ("no_docker", "--no-docker"),
    ],
)
def test_validate_rejects_conflicting_flag(flag, expected_name):
    args = _default_args(package="foo.zip", **{flag: True})

    with pytest.raises(InvalidProjectError) as exc_info:
        _validate_package_flag_combinations(args)

    assert "--package" in str(exc_info.value)
    assert expected_name in str(exc_info.value)


def test_validate_reports_all_conflicting_flags_at_once():
    args = _default_args(
        package="foo.zip", dry_run=True, use_docker=True, no_docker=False
    )

    with pytest.raises(InvalidProjectError) as exc_info:
        _validate_package_flag_combinations(args)

    message = str(exc_info.value)
    assert "--dry-run" in message
    assert "--use-docker" in message


def test_validate_accepts_package_with_only_safe_flags():
    args = _default_args(
        package="foo.zip",
        endpoint_url="https://example",
        region="us-east-1",
        role_arn="arn:aws:iam::123:role/X",
        use_role=True,
        set_default=True,
        profile="default",
    )

    # Should not raise.
    _validate_package_flag_combinations(args)


# ---------------------------------------------------------------------------
# submit() dispatch
# ---------------------------------------------------------------------------


def test_submit_without_package_runs_classic_workflow():
    args = _default_args(package=None)

    with patch("rpdk.core.submit.Project") as mock_project_cls, patch(
        "rpdk.core.submit._submit_existing_package"
    ) as mock_existing:
        project = mock_project_cls.return_value
        project.settings = {}
        submit(args)

    assert project.load.called
    assert project.submit.called
    assert mock_existing.called is False


def test_submit_with_package_delegates_to_existing_package_path():
    args = _default_args(package="foo.zip")

    with patch("rpdk.core.submit._submit_existing_package") as mock_existing, patch(
        "rpdk.core.submit.Project"
    ) as mock_project_cls:
        submit(args)

    mock_existing.assert_called_once_with(args)
    # Classic workflow must not run.
    assert not mock_project_cls.return_value.load.called
    assert not mock_project_cls.return_value.submit.called


# ---------------------------------------------------------------------------
# _submit_existing_package integration
# ---------------------------------------------------------------------------


def test_existing_package_rejects_missing_file(tmp_path):
    missing = tmp_path / "nothing-here.zip"
    args = _default_args(package=str(missing))

    with pytest.raises(InvalidProjectError, match="does not exist"):
        _submit_existing_package(args)


def test_existing_package_rejects_conflicting_flag(tmp_path):
    pkg = _make_valid_zip(tmp_path / "valid.zip")
    args = _default_args(package=str(pkg), dry_run=True)

    with pytest.raises(InvalidProjectError, match="--dry-run"):
        _submit_existing_package(args)


def test_existing_package_calls_upload_with_cli_options(tmp_path):
    pkg = _make_valid_zip(
        tmp_path / "valid.zip",
        artifact_type=ARTIFACT_TYPE_RESOURCE,
        type_name="Acme::Example::Widget",
    )
    args = _default_args(
        package=str(pkg),
        endpoint_url="https://cfn.example",
        region="eu-west-1",
        role_arn="arn:aws:iam::123:role/X",
        use_role=True,
        set_default=True,
        profile="myprofile",
    )

    # The file object passed to _upload is opened inside a ``with`` block in
    # the production code, so by the time the test inspects the mock the
    # file has already been closed. Capture the bytes inside the fake
    # _upload so we can assert on them afterwards.
    captured_bytes = {}

    def fake_upload(self, fileobj, *_args, **_kwargs):
        captured_bytes["data"] = fileobj.read()

    with patch(
        "rpdk.core.project.Project._upload",
        autospec=True,
        side_effect=fake_upload,
    ) as mock_upload:
        _submit_existing_package(args)

    call_args = mock_upload.call_args
    project_self = call_args.args[0]

    assert project_self.type_name == "Acme::Example::Widget"
    assert project_self.artifact_type == ARTIFACT_TYPE_RESOURCE
    # schema must be empty so the auto-role branch never fires
    assert project_self.schema == {}

    # CLI options are forwarded positionally (endpoint_url, region, role_arn,
    # use_role, set_default, profile) exactly as Project.submit does today.
    remaining = call_args.args[2:]
    assert remaining == (
        "https://cfn.example",
        "eu-west-1",
        "arn:aws:iam::123:role/X",
        True,
        True,
        "myprofile",
    )

    # The fileobj passed to _upload must stream back exactly the bytes of
    # the zip on disk.
    assert captured_bytes["data"] == pkg.read_bytes()


def test_existing_package_does_not_invoke_project_load(tmp_path, monkeypatch):
    """The --package path must not depend on a ``.rpdk-config`` in CWD."""
    pkg = _make_valid_zip(tmp_path / "valid.zip")
    # Put us in a directory that has no .rpdk-config at all.
    empty_cwd = tmp_path / "other-dir"
    empty_cwd.mkdir()
    monkeypatch.chdir(empty_cwd)
    assert not (empty_cwd / ".rpdk-config").exists()

    args = _default_args(package=str(pkg), use_role=False)

    with patch("rpdk.core.project.Project.load", autospec=True) as mock_load, patch(
        "rpdk.core.project.Project._upload", autospec=True
    ):
        _submit_existing_package(args)

    assert mock_load.call_count == 0


@pytest.mark.parametrize(
    "artifact_type,type_name",
    [
        (ARTIFACT_TYPE_RESOURCE, "Acme::Example::Widget"),
        (ARTIFACT_TYPE_MODULE, "Acme::Example::Thing::MODULE"),
        (ARTIFACT_TYPE_HOOK, "Acme::Example::HookGuard"),
    ],
)
def test_existing_package_preserves_artifact_type_and_type_name(
    tmp_path, artifact_type, type_name
):
    pkg = _make_valid_zip(
        tmp_path / f"{artifact_type.lower()}.zip",
        artifact_type=artifact_type,
        type_name=type_name,
    )
    args = _default_args(package=str(pkg), use_role=False)

    with patch("rpdk.core.project.Project._upload", autospec=True) as mock_upload:
        _submit_existing_package(args)

    project_self = mock_upload.call_args.args[0]
    assert project_self.artifact_type == artifact_type
    assert project_self.type_name == type_name


def test_existing_package_surfaces_upload_errors(tmp_path):
    pkg = _make_valid_zip(tmp_path / "valid.zip")
    args = _default_args(package=str(pkg), use_role=False)

    class FakeApiError(RuntimeError):
        pass

    with patch(
        "rpdk.core.project.Project._upload",
        autospec=True,
        side_effect=FakeApiError("Unknown CloudFormation error"),
    ):
        with pytest.raises(FakeApiError, match="CloudFormation"):
            _submit_existing_package(args)


# ANY is imported above because some future assertions may need it; keep the
# import from being flagged as unused.
_ = ANY
