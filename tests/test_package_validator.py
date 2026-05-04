# Tests for rpdk.core.package_validator
#
# pylint: disable=protected-access,redefined-outer-name
"""Unit tests for :mod:`rpdk.core.package_validator`.

These tests cover the ``cfn submit --package`` workflow: validating that a
pre-built zip file declares a supported artifact type and ships the entries
that ``RegisterType`` needs.
"""
import json
import logging
import zipfile
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Mapping, Optional

import pytest

from rpdk.core.exceptions import InvalidProjectError
from rpdk.core.package_validator import (
    ARTIFACT_TYPE_HOOK,
    ARTIFACT_TYPE_MODULE,
    ARTIFACT_TYPE_RESOURCE,
    METADATA_FILENAME,
    SCHEMA_FILENAME,
    SETTINGS_FILENAME,
    PackageMetadata,
    PackageValidator,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_zip(path: Path, entries: Optional[Mapping[str, object]] = None) -> Path:
    """Write a zip at ``path`` with ``entries``. Values may be str, bytes, or
    pre-serialized JSON via a helper.

    A value of ``None`` means "do not write this entry". ``entries=None`` or
    omitted writes an empty zip.
    """
    entries = entries or {}
    with zipfile.ZipFile(path, mode="w") as zf:
        for name, content in entries.items():
            if content is None:
                continue
            if isinstance(content, bytes):
                zf.writestr(name, content)
            else:
                zf.writestr(name, content)
    return path


def _valid_settings(
    artifact_type: str = ARTIFACT_TYPE_RESOURCE,
    type_name: str = "Acme::Example::Widget",
) -> str:
    return json.dumps({"typeName": type_name, "artifact_type": artifact_type})


def _schema(type_name: str = "Acme::Example::Widget") -> str:
    return json.dumps({"typeName": type_name})


# ---------------------------------------------------------------------------
# PackageMetadata
# ---------------------------------------------------------------------------


def test_package_metadata_is_frozen():
    meta = PackageMetadata(
        path=Path("/tmp/x.zip"),
        type_name="A::B::C",
        artifact_type=ARTIFACT_TYPE_RESOURCE,
    )
    with pytest.raises(FrozenInstanceError):
        meta.type_name = "X::Y::Z"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# validate() happy paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "artifact_type,type_name",
    [
        (ARTIFACT_TYPE_RESOURCE, "Acme::Example::Widget"),
        (ARTIFACT_TYPE_MODULE, "Acme::Example::Thing::MODULE"),
        (ARTIFACT_TYPE_HOOK, "Acme::Example::HookGuard"),
    ],
)
def test_validate_returns_metadata_for_each_artifact_type(
    tmp_path, artifact_type, type_name
):
    pkg = _write_zip(
        tmp_path / f"{artifact_type.lower()}.zip",
        {
            SETTINGS_FILENAME: _valid_settings(artifact_type, type_name),
            SCHEMA_FILENAME: _schema(type_name),
        },
    )

    result = PackageValidator(pkg).validate()

    assert result == PackageMetadata(
        path=pkg, type_name=type_name, artifact_type=artifact_type
    )


def test_validate_treats_missing_artifact_type_as_resource(tmp_path):
    """Legacy packages were written without ``artifact_type``. They must be
    accepted and treated as RESOURCE for backward compatibility.
    """
    pkg = _write_zip(
        tmp_path / "legacy.zip",
        {
            SETTINGS_FILENAME: json.dumps({"typeName": "Legacy::Example::Thing"}),
            SCHEMA_FILENAME: _schema("Legacy::Example::Thing"),
        },
    )

    result = PackageValidator(pkg).validate()

    assert result.artifact_type == ARTIFACT_TYPE_RESOURCE
    assert result.type_name == "Legacy::Example::Thing"


# ---------------------------------------------------------------------------
# validate() error paths
# ---------------------------------------------------------------------------


def test_validate_rejects_missing_path(tmp_path):
    missing = tmp_path / "does-not-exist.zip"

    with pytest.raises(InvalidProjectError, match="does not exist"):
        PackageValidator(missing).validate()


def test_validate_rejects_non_zip_file(tmp_path):
    non_zip = tmp_path / "not-a-zip.bin"
    non_zip.write_bytes(b"these bytes are not a zip archive")

    with pytest.raises(InvalidProjectError, match="not a valid zip archive"):
        PackageValidator(non_zip).validate()


def test_validate_rejects_missing_rpdk_config(tmp_path):
    pkg = _write_zip(
        tmp_path / "no-settings.zip",
        {SCHEMA_FILENAME: _schema()},
    )

    with pytest.raises(
        InvalidProjectError, match=r"missing required entry '\.rpdk-config'"
    ):
        PackageValidator(pkg).validate()


def test_validate_rejects_invalid_json_in_settings(tmp_path):
    pkg = _write_zip(
        tmp_path / "bad-json.zip",
        {
            SETTINGS_FILENAME: "{not json",
            SCHEMA_FILENAME: _schema(),
        },
    )

    with pytest.raises(InvalidProjectError, match="is not valid JSON"):
        PackageValidator(pkg).validate()


def test_validate_rejects_unknown_artifact_type(tmp_path):
    pkg = _write_zip(
        tmp_path / "bad-artifact.zip",
        {
            SETTINGS_FILENAME: json.dumps(
                {"typeName": "A::B::C", "artifact_type": "FOO"}
            ),
            SCHEMA_FILENAME: _schema("A::B::C"),
        },
    )

    with pytest.raises(
        InvalidProjectError,
        match=r"unsupported artifact_type 'FOO'",
    ):
        PackageValidator(pkg).validate()


def test_validate_rejects_missing_type_name(tmp_path):
    pkg = _write_zip(
        tmp_path / "no-type-name.zip",
        {
            SETTINGS_FILENAME: json.dumps({"artifact_type": ARTIFACT_TYPE_RESOURCE}),
            SCHEMA_FILENAME: _schema(),
        },
    )

    with pytest.raises(
        InvalidProjectError,
        match=r"missing required field 'typeName'",
    ):
        PackageValidator(pkg).validate()


def test_validate_rejects_missing_schema_json(tmp_path):
    pkg = _write_zip(
        tmp_path / "no-schema.zip",
        {SETTINGS_FILENAME: _valid_settings()},
    )

    with pytest.raises(
        InvalidProjectError,
        match=r"missing required entry 'schema\.json'",
    ):
        PackageValidator(pkg).validate()


# ---------------------------------------------------------------------------
# Metadata file - best-effort, never fatal
# ---------------------------------------------------------------------------


def test_validate_logs_cli_version_when_metadata_present(tmp_path, caplog):
    pkg = _write_zip(
        tmp_path / "with-metadata.zip",
        {
            SETTINGS_FILENAME: _valid_settings(),
            SCHEMA_FILENAME: _schema(),
            METADATA_FILENAME: json.dumps({"cli-version": "1.2.3"}),
        },
    )

    with caplog.at_level(logging.INFO, logger="rpdk.core.package_validator"):
        PackageValidator(pkg).validate()

    logged = [
        record.getMessage()
        for record in caplog.records
        if record.name == "rpdk.core.package_validator"
    ]
    assert any("1.2.3" in message for message in logged), logged


def test_validate_tolerates_broken_metadata_json(tmp_path, caplog):
    pkg = _write_zip(
        tmp_path / "broken-metadata.zip",
        {
            SETTINGS_FILENAME: _valid_settings(),
            SCHEMA_FILENAME: _schema(),
            METADATA_FILENAME: "{not json",
        },
    )

    # should not raise
    with caplog.at_level(logging.WARNING, logger="rpdk.core.package_validator"):
        result = PackageValidator(pkg).validate()

    assert result.type_name == "Acme::Example::Widget"
    assert any(
        "could not be parsed as JSON" in record.getMessage()
        for record in caplog.records
        if record.name == "rpdk.core.package_validator"
    )


def test_validate_tolerates_metadata_without_cli_version(tmp_path, caplog):
    pkg = _write_zip(
        tmp_path / "metadata-without-version.zip",
        {
            SETTINGS_FILENAME: _valid_settings(),
            SCHEMA_FILENAME: _schema(),
            METADATA_FILENAME: json.dumps({"other-field": "value"}),
        },
    )

    with caplog.at_level(logging.WARNING, logger="rpdk.core.package_validator"):
        PackageValidator(pkg).validate()

    assert any(
        "without a 'cli-version' field" in record.getMessage()
        for record in caplog.records
        if record.name == "rpdk.core.package_validator"
    )


def test_validate_tolerates_metadata_that_is_not_a_json_object(tmp_path, caplog):
    pkg = _write_zip(
        tmp_path / "metadata-list.zip",
        {
            SETTINGS_FILENAME: _valid_settings(),
            SCHEMA_FILENAME: _schema(),
            METADATA_FILENAME: json.dumps(["list", "instead", "of", "object"]),
        },
    )

    with caplog.at_level(logging.WARNING, logger="rpdk.core.package_validator"):
        PackageValidator(pkg).validate()

    assert any(
        "not a JSON object" in record.getMessage()
        for record in caplog.records
        if record.name == "rpdk.core.package_validator"
    )


def test_validate_succeeds_silently_when_metadata_absent(tmp_path, caplog):
    pkg = _write_zip(
        tmp_path / "no-metadata.zip",
        {
            SETTINGS_FILENAME: _valid_settings(),
            SCHEMA_FILENAME: _schema(),
        },
    )

    with caplog.at_level(logging.DEBUG, logger="rpdk.core.package_validator"):
        PackageValidator(pkg).validate()

    # No log record from this module should be emitted in the "happy, no metadata"
    # case. Other loggers are not our concern.
    logs_from_module = [
        record
        for record in caplog.records
        if record.name == "rpdk.core.package_validator"
    ]
    assert logs_from_module == []
