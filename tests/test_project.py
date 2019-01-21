# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,useless-super-delegation,protected-access
import json
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.stub import Stubber
from jsonschema.exceptions import ValidationError

from rpdk.cli import EXIT_UNHANDLED_EXCEPTION
from rpdk.project import HANDLER_OPS, RESOURCE_EXISTS_MSG, InvalidSettingsError, Project

LANGUAGE = "BQHDBC"
CONTENTS_UTF8 = "💣"
TYPE_NAME = "AWS::Color::Red"
ARN = "SOMEARN"
SCHEMA = {}
EXPECTED_REGISTRY_ARGS = {
    "TypeName": TYPE_NAME,
    "Schema": json.dumps(SCHEMA),
    "Handlers": {op: ARN for op in HANDLER_OPS},
    "Documentation": "Docs",
}


@pytest.fixture
def project():
    return Project()


@pytest.fixture
def submit_project():
    project = Project()
    project.type_name = TYPE_NAME
    project.schema = SCHEMA
    return project


@contextmanager
def patch_settings(project, data):
    with patch.object(project, "settings_path", autospec=True) as mock_path:
        mock_path.open.return_value.__enter__.return_value = StringIO(data)
        yield mock_path.open


def test_load_settings_invalid_json(project):
    with patch_settings(project, "") as mock_open:
        with pytest.raises(InvalidSettingsError):
            project.load_settings()
    mock_open.assert_called_once_with("r", encoding="utf-8")


def test_load_settings_invalid_settings(project):
    with patch_settings(project, "{}") as mock_open:
        with pytest.raises(InvalidSettingsError):
            project.load_settings()
    mock_open.assert_called_once_with("r", encoding="utf-8")


def test_load_settings_valid_json(project):
    plugin = object()
    data = json.dumps({"typeName": TYPE_NAME, "language": LANGUAGE})
    patch_load = patch("rpdk.project.load_plugin", autospec=True, return_value=plugin)

    with patch_settings(project, data) as mock_open, patch_load as mock_load:
        project.load_settings()

    mock_open.assert_called_once_with("r", encoding="utf-8")
    mock_load.assert_called_once_with(LANGUAGE)
    assert project.type_info == ("AWS", "Color", "Red")
    assert project.type_name == TYPE_NAME
    assert project._plugin is plugin
    assert project.settings == {}


def test_load_schema_settings_not_loaded(project):
    with pytest.raises(RuntimeError):
        project.load_schema()


def test_load_schema_example(tmpdir):
    project = Project(root=tmpdir)
    project.type_name = "AWS::Color::Blue"
    project._write_example_schema()
    project.load_schema()


def test_overwrite():
    mock_path = MagicMock(spec=Path)
    Project.overwrite(mock_path, LANGUAGE)

    mock_path.open.assert_called_once_with("w", encoding="utf-8")
    mock_f = mock_path.open.return_value.__enter__.return_value
    mock_f.write.assert_called_once_with(LANGUAGE)


def test_safewrite_overwrite(project):
    path = object()
    contents = object()

    patch_attr = patch.object(project, "_overwrite", True)
    patch_meth = patch.object(project, "overwrite", autospec=True)
    with patch_attr, patch_meth as mock_overwrite:
        project.safewrite(path, contents)

    mock_overwrite.assert_called_once_with(path, contents)


def test_safewrite_doesnt_exist(project, tmpdir):
    path = Path(tmpdir.join("test")).resolve()

    with patch.object(project, "_overwrite", False):
        project.safewrite(path, CONTENTS_UTF8)

    with path.open("r", encoding="utf-8") as f:
        assert f.read() == CONTENTS_UTF8


def test_safewrite_exists(project, tmpdir, caplog):
    path = Path(tmpdir.join("test")).resolve()

    with path.open("w", encoding="utf-8") as f:
        f.write(CONTENTS_UTF8)

    with patch.object(project, "_overwrite", False):
        project.safewrite(path, CONTENTS_UTF8)

    last_record = caplog.records[-1]
    assert last_record.levelname == "WARNING"
    assert str(path) in last_record.message


def test_generate(project):
    mock_plugin = MagicMock(spec=["generate"])
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
    mock_plugin.generate.assert_called_once_with(project)


def test_init(tmpdir):
    type_name = "AWS::Color::Red"

    mock_plugin = MagicMock(spec=["init"])
    patch_load_plugin = patch(
        "rpdk.project.load_plugin", autospec=True, return_value=mock_plugin
    )

    project = Project(root=tmpdir)
    with patch_load_plugin as mock_load_plugin:
        project.init(type_name, LANGUAGE)

    mock_load_plugin.assert_called_once_with(LANGUAGE)
    mock_plugin.init.assert_called_once_with(project)

    assert project.type_info == ("AWS", "Color", "Red")
    assert project.type_name == type_name
    assert project._plugin is mock_plugin
    assert project.settings == {}

    with project.settings_path.open("r", encoding="utf-8") as f:
        assert json.load(f)

    with project.schema_path.open("r", encoding="utf-8") as f:
        assert json.load(f)


def test_package(project):
    project.type_name = TYPE_NAME
    mock_plugin = MagicMock(spec=["package"])
    mock_plugin.NAME = LANGUAGE

    plugin = patch.object(project, "_plugin", mock_plugin)
    package = patch("rpdk.project.package_handler", autospec=True, return_value=ARN)
    write = patch.object(project, "_write_settings", autospec=True)
    submit = patch.object(project, "submit")
    with plugin, package as mock_package, write as mock_write, submit as mock_submit:
        project.package()

    mock_plugin.package.assert_called_once_with(project)
    stack_name = "{}-stack".format(project.hypenated_name)
    mock_package.assert_called_once_with(stack_name)
    mock_submit.assert_called_once_with(ARN)
    mock_write.assert_called_once_with(LANGUAGE)


def test_submit(submit_project):
    client = boto3.client("cloudformation")
    stubber = Stubber(client)
    stubber.add_response("create_resource_type", {"Arn": ARN}, EXPECTED_REGISTRY_ARGS)

    with patch("rpdk.project.create_registry_client", return_value=client), stubber:
        arn = submit_project.submit(ARN)
    stubber.assert_no_pending_responses()

    assert arn == ARN


def test_update_submit(submit_project):
    client = boto3.client("cloudformation")
    stubber = Stubber(client)
    stubber.add_client_error(
        "create_resource_type",
        service_error_code="CFNRegistryException",
        service_message=RESOURCE_EXISTS_MSG,
    )
    stubber.add_response("update_resource_type", {"Arn": ARN}, EXPECTED_REGISTRY_ARGS)
    with patch("rpdk.project.create_registry_client", return_value=client), stubber:
        arn = submit_project.submit(ARN)
    stubber.assert_no_pending_responses()

    assert arn == ARN


def test_fail_submit(submit_project):
    client = boto3.client("cloudformation")
    stubber = Stubber(client)

    stubber.add_client_error(
        "create_resource_type",
        service_error_code="CFNRegistryException",
        service_message="Unhandled Exception",
    )
    with patch(
        "rpdk.project.create_registry_client", return_value=client
    ), stubber, pytest.raises(client.exceptions.CFNRegistryException):
        submit_project.submit(ARN)
    stubber.assert_no_pending_responses()


def test_load_invalid_schema(project, caplog):
    patch_settings = patch.object(project, "load_settings")
    patch_schema = patch.object(project, "load_schema", side_effect=ValidationError(""))
    with patch_settings as mock_settings, patch_schema as mock_schema, pytest.raises(
        SystemExit
    ) as excinfo:
        project.load()

    last_record = caplog.records[-1]
    mock_settings.assert_called_once_with()
    mock_schema.assert_called_once_with()

    assert excinfo.value.code != EXIT_UNHANDLED_EXCEPTION
    assert "invalid" in last_record.message


def test_schema_not_found(project, caplog):
    patch_settings = patch.object(project, "load_settings")
    patch_schema = patch.object(project, "load_schema", side_effect=FileNotFoundError)
    with patch_settings as mock_settings, patch_schema as mock_schema, pytest.raises(
        SystemExit
    ) as excinfo:
        project.load()

    last_record = caplog.records[-1]
    mock_settings.assert_called_once_with()
    mock_schema.assert_called_once_with()

    assert excinfo.value.code != EXIT_UNHANDLED_EXCEPTION
    assert all(
        keyword in last_record.message for keyword in ("not found", "specification")
    )


def test_settings_not_found(project, caplog):
    patch_settings = patch.object(
        project, "load_settings", side_effect=FileNotFoundError
    )
    patch_schema = patch.object(project, "load_schema")

    with patch_settings as mock_settings, patch_schema as mock_schema, pytest.raises(
        SystemExit
    ) as excinfo:
        project.load()

    assert excinfo.value.code != EXIT_UNHANDLED_EXCEPTION
    mock_settings.assert_called_once_with()
    mock_schema.assert_not_called()
    last_record = caplog.records[-1]

    assert all(keyword in last_record.message for keyword in ("not found", "init"))
