# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,useless-super-delegation,protected-access
# pylint: disable=too-many-lines
import json
import logging
import os
import random
import string
import zipfile
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from shutil import copyfile
from unittest.mock import ANY, MagicMock, patch

import pytest
import yaml
from botocore.exceptions import ClientError, WaiterError

from rpdk.core.data_loaders import resource_json, resource_stream
from rpdk.core.exceptions import (
    DownstreamError,
    FragmentValidationError,
    InternalError,
    InvalidProjectError,
    SpecValidationError,
)
from rpdk.core.plugin_base import LanguagePlugin
from rpdk.core.project import (
    CFN_METADATA_FILENAME,
    LAMBDA_RUNTIMES,
    OVERRIDES_FILENAME,
    SCHEMA_UPLOAD_FILENAME,
    SETTINGS_FILENAME,
    Project,
    escape_markdown,
)
from rpdk.core.test import empty_override
from rpdk.core.upload import Uploader

from .utils import CONTENTS_UTF8, UnclosingBytesIO

ARTIFACT_TYPE_RESOURCE = "RESOURCE"
ARTIFACT_TYPE_MODULE = "MODULE"
LANGUAGE = "BQHDBC"
TYPE_NAME = "AWS::Color::Red"
MODULE_TYPE_NAME = "AWS::Color::Red::MODULE"
REGION = "us-east-1"
ENDPOINT = "cloudformation.beta.com"
RUNTIME = random.choice(list(LAMBDA_RUNTIMES))
BLANK_CLIENT_ERROR = {"Error": {"Code": "", "Message": ""}}
LOG = logging.getLogger(__name__)
REGISTRATION_TOKEN = "foo"
TYPE_ARN = "arn:aws:cloudformation:us-east-1:123456789012:type/resource/Foo-Bar-Foo"
TYPE_VERSION_ARN = (
    "arn:aws:cloudformation:us-east-1:123456789012:type/resource/Foo-Bar-Foo/00000001"
)
DESCRIBE_TYPE_COMPLETE_RETURN = {
    "TypeArn": TYPE_ARN,
    "TypeVersionArn": TYPE_VERSION_ARN,
    "Description": "Some detailed progress message.",
    "ProgressStatus": "COMPLETE",
}
DESCRIBE_TYPE_FAILED_RETURN = {
    "Description": "Some detailed progress message.",
    "ProgressStatus": "FAILED",
}
CREATE_INPUTS_FILE = "inputs/inputs_1_create.json"
UPDATE_INPUTS_FILE = "inputs/inputs_1_update.json"
INVALID_INPUTS_FILE = "inputs/inputs_1_invalid.json"

PLUGIN_INFORMATION = {
    "plugin-version": "2.1.3",
    "plugin-tool-version": "2.0.8",
    "plugin-name": "java",
}


@pytest.mark.parametrize("string", ["^[a-z]$", "([a-z])", ".*", "*."])
def test_escape_markdown_with_regex_names(string):
    assert escape_markdown(string).startswith("\\")


def test_escape_markdown_with_empty_string():
    assert escape_markdown("") == ""
    assert escape_markdown(None) is None


@pytest.mark.parametrize("string", ["Hello", "SomeProperty"])
def test_escape_markdown(string):
    assert escape_markdown(string) == string


@pytest.fixture
def project(tmpdir):
    unique_dir = "".join(random.choices(string.ascii_uppercase, k=12))
    return Project(root=tmpdir.mkdir(unique_dir))


@contextmanager
def patch_settings(project, data):
    with patch.object(project, "settings_path", autospec=True) as mock_path:
        mock_path.open.return_value.__enter__.return_value = StringIO(data)
        yield mock_path.open


def test_load_settings_invalid_json(project):
    with patch_settings(project, "") as mock_open:
        with pytest.raises(InvalidProjectError):
            project.load_settings()
    mock_open.assert_called_once_with("r", encoding="utf-8")


def test_load_settings_invalid_settings(project):
    with patch_settings(project, "{}") as mock_open:
        with pytest.raises(InvalidProjectError):
            project.load_settings()
    mock_open.assert_called_once_with("r", encoding="utf-8")


def test_load_settings_invalid_modules_settings(project):
    with patch_settings(project, '{"artifact_type": "MODULE"}') as mock_open:
        with pytest.raises(InvalidProjectError):
            project.load_settings()
    mock_open.assert_called_once_with("r", encoding="utf-8")


def test_load_settings_valid_json_for_resource(project):
    plugin = object()
    data = json.dumps(
        {
            "artifact_type": "RESOURCE",
            "typeName": TYPE_NAME,
            "language": LANGUAGE,
            "runtime": RUNTIME,
            "entrypoint": None,
            "testEntrypoint": None,
            "futureProperty": "value",
        }
    )
    patch_load = patch(
        "rpdk.core.project.load_plugin", autospec=True, return_value=plugin
    )

    with patch_settings(project, data) as mock_open, patch_load as mock_load:
        project.load_settings()

    mock_open.assert_called_once_with("r", encoding="utf-8")
    mock_load.assert_called_once_with(LANGUAGE)
    assert project.type_info == ("AWS", "Color", "Red")
    assert project.type_name == TYPE_NAME
    assert project.language == LANGUAGE
    assert project.artifact_type == ARTIFACT_TYPE_RESOURCE
    assert project._plugin is plugin
    assert project.settings == {}


def test_load_settings_valid_json_for_resource_backward_compatible(project):
    plugin = object()
    data = json.dumps(
        {
            "typeName": TYPE_NAME,
            "language": LANGUAGE,
            "runtime": RUNTIME,
            "entrypoint": None,
            "testEntrypoint": None,
        }
    )
    patch_load = patch(
        "rpdk.core.project.load_plugin", autospec=True, return_value=plugin
    )

    with patch_settings(project, data) as mock_open, patch_load as mock_load:
        project.load_settings()

    mock_open.assert_called_once_with("r", encoding="utf-8")
    mock_load.assert_called_once_with(LANGUAGE)
    assert project.type_info == ("AWS", "Color", "Red")
    assert project.type_name == TYPE_NAME
    assert project.language == LANGUAGE
    assert project.artifact_type == ARTIFACT_TYPE_RESOURCE
    assert project._plugin is plugin
    assert project.settings == {}


def test_load_settings_valid_json_for_module(project):
    plugin = object()
    data = json.dumps(
        {
            "artifact_type": "MODULE",
            "typeName": MODULE_TYPE_NAME,
        }
    )
    patch_load = patch(
        "rpdk.core.project.load_plugin", autospec=True, return_value=plugin
    )

    with patch_settings(project, data) as mock_open, patch_load as mock_load:
        project.load_settings()

    mock_open.assert_called_once_with("r", encoding="utf-8")
    mock_load.assert_not_called()
    assert project.type_info == ("AWS", "Color", "Red", "MODULE")
    assert project.type_name == MODULE_TYPE_NAME
    assert project.language is None
    assert project.artifact_type == ARTIFACT_TYPE_MODULE
    assert project._plugin is None
    assert project.settings == {}


def test_generate_for_modules_succeeds(project):
    project.type_info = ("AWS", "Color", "Red", "MODULE")
    project.artifact_type = ARTIFACT_TYPE_MODULE
    project.generate()
    project.generate_docs()


def test_load_schema_settings_not_loaded(project):
    with pytest.raises(InternalError):
        project.load_schema()


def test_load_schema_example(project):
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

    patch_attr = patch.object(project, "overwrite_enabled", True)
    patch_meth = patch.object(project, "overwrite", autospec=True)
    with patch_attr, patch_meth as mock_overwrite:
        project.safewrite(path, contents)

    mock_overwrite.assert_called_once_with(path, contents)


def test_safewrite_doesnt_exist(project, tmpdir):
    path = Path(tmpdir.join("test")).resolve()

    with patch.object(project, "overwrite_enabled", False):
        project.safewrite(path, CONTENTS_UTF8)

    with path.open("r", encoding="utf-8") as f:
        assert f.read() == CONTENTS_UTF8


def test_safewrite_exists(project, tmpdir, caplog):
    caplog.set_level(logging.INFO)
    path = Path(tmpdir.join("test")).resolve()

    with path.open("w", encoding="utf-8") as f:
        f.write(CONTENTS_UTF8)

    with patch.object(project, "overwrite_enabled", False):
        project.safewrite(path, CONTENTS_UTF8)

    last_record = caplog.records[-1]
    assert last_record.levelname == "INFO"
    assert str(path) in last_record.message


def test_generate_no_handlers(project):
    project.schema = {}
    mock_plugin = MagicMock(spec=["generate"])
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
        project.generate_docs()
    mock_plugin.generate.assert_called_once_with(project)


@pytest.mark.parametrize(
    "schema_path,path",
    [
        ("data/schema/valid/valid_no_type.json", "generate_with_no_type_defined"),
        (
            "data/schema/valid/valid_type_complex.json",
            "generate_with_docs_type_complex",
        ),
        (
            "data/schema/valid/valid_pattern_properties.json",
            "generate_with_docs_pattern_properties",
        ),
        (
            "data/schema/valid/valid_no_properties.json",
            "generate_with_docs_no_properties",
        ),
        (
            "data/schema/valid/valid_nested_property_object.json",
            "generate_with_docs_nested_object",
        ),
        (
            "data/schema/valid/valid_type_composite_primary_identifier.json",
            "generate_with_docs_composite_primary_identifier",
        ),
    ],
)
def test_generate_with_docs(project, tmp_path_factory, schema_path, path):
    project.schema = resource_json(__name__, schema_path)
    project.type_name = "AWS::Color::Red"
    # tmpdir conflicts with other tests, make a unique one
    project.root = tmp_path_factory.mktemp(path)
    mock_plugin = MagicMock(spec=["generate"])
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
        project.generate_docs()
    mock_plugin.generate.assert_called_once_with(project)

    docs_dir = project.root / "docs"
    readme_file = project.root / "docs" / "README.md"

    assert docs_dir.is_dir()
    assert readme_file.is_file()
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
    readme_contents = readme_file.read_text(encoding="utf-8")
    assert project.type_name in readme_contents


def test_generate_docs_with_multityped_property(project, tmp_path_factory):
    project.schema = resource_json(
        __name__, "data/schema/valid/valid_multityped_property.json"
    )

    project.type_name = "AWS::Color::Red"
    # tmpdir conflicts with other tests, make a unique one
    project.root = tmp_path_factory.mktemp("generate_with_docs_type_complex")
    mock_plugin = MagicMock(spec=["generate"])
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
        project.generate_docs()
    mock_plugin.generate.assert_called_once_with(project)

    docs_dir = project.root / "docs"
    readme_file = project.root / "docs" / "README.md"

    assert docs_dir.is_dir()
    assert readme_file.is_file()
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
    readme_contents = readme_file.read_text(encoding="utf-8")
    readme_contents_target = resource_stream(
        __name__, "data/schema/target_output/multityped.md"
    )

    read_me_stripped = readme_contents.strip().replace(" ", "")
    read_me_target_stripped = readme_contents_target.read().strip().replace(" ", "")

    LOG.debug("read_me_stripped %s", read_me_stripped)
    LOG.debug("read_me_target_stripped %s", read_me_target_stripped)

    assert project.type_name in readme_contents
    assert read_me_stripped == read_me_target_stripped


def test_generate_docs_with_multiref_property(project, tmp_path_factory):
    project.schema = resource_json(
        __name__, "data/schema/valid/valid_multiref_property.json"
    )

    project.type_name = "AWS::Color::Red"
    # tmpdir conflicts with other tests, make a unique one
    project.root = tmp_path_factory.mktemp("generate_with_docs_type_complex")
    mock_plugin = MagicMock(spec=["generate"])
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
        project.generate_docs()
    mock_plugin.generate.assert_called_once_with(project)

    docs_dir = project.root / "docs"
    readme_file = project.root / "docs" / "README.md"

    assert docs_dir.is_dir()
    assert readme_file.is_file()
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
    readme_contents = readme_file.read_text(encoding="utf-8")
    readme_contents_target = resource_stream(
        __name__, "data/schema/target_output/multiref.md"
    )

    read_me_stripped = readme_contents.strip().replace(" ", "")
    read_me_target_stripped = readme_contents_target.read().strip().replace(" ", "")

    LOG.debug("read_me_stripped %s", read_me_stripped)
    LOG.debug("read_me_target_stripped %s", read_me_target_stripped)

    assert project.type_name in readme_contents
    assert read_me_stripped == read_me_target_stripped


def test_generate_with_docs_invalid_property_type(project, tmp_path_factory):
    project.schema = resource_json(
        __name__, "data/schema/invalid/invalid_property_type_invalid.json"
    )
    project.type_name = "AWS::Color::Red"
    # tmpdir conflicts with other tests, make a unique one
    project.root = tmp_path_factory.mktemp("generate_with_docs_invalid_property_type")
    mock_plugin = MagicMock(spec=["generate"])
    with patch.object(project, "_plugin", mock_plugin):
        # skip actual generation
        project.generate_docs()

    docs_dir = project.root / "docs"
    readme_file = project.root / "docs" / "README.md"

    assert docs_dir.is_dir()
    assert readme_file.is_file()
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
        project.generate_docs()
    readme_contents = readme_file.read_text(encoding="utf-8")
    assert project.type_name in readme_contents


def test_generate_with_docs_no_type(project, tmp_path_factory):
    project.schema = {"properties": {}}
    # tmpdir conflicts with other tests, make a unique one
    project.root = tmp_path_factory.mktemp("generate_with_docs_no_type")
    mock_plugin = MagicMock(spec=["generate"])
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
        project.generate_docs()
    mock_plugin.generate.assert_called_once_with(project)

    docs_dir = project.root / "docs"

    assert not docs_dir.is_dir()


def test_generate_with_docs_twice(project, tmp_path_factory):
    project.schema = {"properties": {}}
    project.type_name = "AWS::Color::Red"
    # tmpdir conflicts with other tests, make a unique one
    project.root = tmp_path_factory.mktemp("generate_with_docs_twice")
    mock_plugin = MagicMock(spec=["generate"])
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
        project.generate_docs()
    mock_plugin.generate.assert_called_once_with(project)

    docs_dir = project.root / "docs"
    readme_file = docs_dir / "README.md"

    assert docs_dir.is_dir()
    assert readme_file.is_file()
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
        project.generate_docs()
    assert docs_dir.is_dir()
    assert readme_file.is_file()
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
        project.generate_docs()
    readme_contents = readme_file.read_text(encoding="utf-8")
    assert project.type_name in readme_contents


def test_generate_handlers(project, tmpdir):
    project.type_name = "Test::Handler::Test"
    expected_actions = {"createAction", "readAction"}
    project.schema = {
        "handlers": {
            "create": {"permissions": ["createAction", "readAction"]},
            "read": {"permissions": ["readAction", ""]},
        }
    }
    project.root = tmpdir
    mock_plugin = MagicMock(spec=["generate"])
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()

    role_path = project.root / "resource-role.yaml"
    with role_path.open("r", encoding="utf-8") as f:
        template = yaml.safe_load(f.read())

    action_list = template["Resources"]["ExecutionRole"]["Properties"]["Policies"][0][
        "PolicyDocument"
    ]["Statement"][0]["Action"]

    assert all(action in expected_actions for action in action_list)
    assert len(action_list) == len(expected_actions)
    assert template["Outputs"]["ExecutionRoleArn"]
    mock_plugin.generate.assert_called_once_with(project)


@pytest.mark.parametrize(
    "schema",
    ({"handlers": {"create": {"permissions": [""]}}}, {"handlers": {"create": {}}}),
)
def test_generate_handlers_deny_all(project, tmpdir, schema):
    project.type_name = "Test::Handler::Test"
    project.schema = schema
    project.root = tmpdir
    mock_plugin = MagicMock(spec=["generate"])
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()

    role_path = project.root / "resource-role.yaml"
    with role_path.open("r", encoding="utf-8") as f:
        template = yaml.safe_load(f.read())

    statement = template["Resources"]["ExecutionRole"]["Properties"]["Policies"][0][
        "PolicyDocument"
    ]["Statement"][0]
    assert statement["Effect"] == "Deny"
    assert statement["Action"][0] == "*"
    mock_plugin.generate.assert_called_once_with(project)


@pytest.mark.parametrize(
    "schema,result",
    (
        ({"handlers": {"create": {"timeoutInMinutes": 720}}}, 43200),
        ({"handlers": {"create": {"timeoutInMinutes": 2}}}, 3600),
        ({"handlers": {"create": {"timeoutInMinutes": 90}}}, 6300),
        (
            {
                "handlers": {
                    "create": {"timeoutInMinutes": 70},
                    "update": {"timeoutInMinutes": 90},
                }
            },
            6300,
        ),
        ({"handlers": {"create": {}}}, 8400),
        ({"handlers": {"create": {"timeoutInMinutes": 90}, "read": {}}}, 8400),
    ),
)
def test_generate_handlers_role_session_timeout(project, tmpdir, schema, result):
    project.type_name = "Test::Handler::Test"
    project.schema = schema
    project.root = tmpdir
    mock_plugin = MagicMock(spec=["generate"])
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()

    role_path = project.root / "resource-role.yaml"
    with role_path.open("r", encoding="utf-8") as f:
        template = yaml.safe_load(f.read())

    max_session_timeout = template["Resources"]["ExecutionRole"]["Properties"][
        "MaxSessionDuration"
    ]
    assert max_session_timeout == result

    mock_plugin.generate.assert_called_once_with(project)


def test_init_resource(project):
    type_name = "AWS::Color::Red"

    mock_plugin = MagicMock(spec=["init"])
    patch_load_plugin = patch(
        "rpdk.core.project.load_plugin", autospec=True, return_value=mock_plugin
    )

    with patch_load_plugin as mock_load_plugin:
        project.init(type_name, LANGUAGE)

    mock_load_plugin.assert_called_once_with(LANGUAGE)
    mock_plugin.init.assert_called_once_with(project)

    assert project.type_info == ("AWS", "Color", "Red")
    assert project.type_name == type_name
    assert project.language == LANGUAGE
    assert project.artifact_type == ARTIFACT_TYPE_RESOURCE
    assert project._plugin is mock_plugin
    assert project.settings == {}

    with project.settings_path.open("r", encoding="utf-8") as f:
        assert json.load(f)

    # ends with newline
    with project.settings_path.open("rb") as f:
        f.seek(-1, os.SEEK_END)
        assert f.read() == b"\n"

    with project.schema_path.open("r", encoding="utf-8") as f:
        assert json.load(f)

    for file_inputs in (
        "inputs_1_create.json",
        "inputs_1_update.json",
        "inputs_1_invalid.json",
    ):
        path_file = project.example_inputs_path / file_inputs
        with path_file.open("r", encoding="utf-8") as f:
            assert json.load(f)

    # ends with newline
    with project.schema_path.open("rb") as f:
        f.seek(-1, os.SEEK_END)
        assert f.read() == b"\n"


def test_init_module(project):
    type_name = "AWS::Color::Red"

    mock_plugin = MagicMock(spec=["init"])
    patch_load_plugin = patch(
        "rpdk.core.project.load_plugin", autospec=True, return_value=mock_plugin
    )

    with patch_load_plugin as mock_load_plugin:
        project.init_module(type_name)

    mock_load_plugin.assert_not_called()
    mock_plugin.init.assert_not_called()

    assert project.type_info == ("AWS", "Color", "Red")
    assert project.type_name == type_name
    assert project.language is None
    assert project.artifact_type == ARTIFACT_TYPE_MODULE
    assert project._plugin is None
    assert project.settings == {}

    with project.settings_path.open("r", encoding="utf-8") as f:
        assert json.load(f)

    # ends with newline
    with project.settings_path.open("rb") as f:
        f.seek(-1, os.SEEK_END)
        assert f.read() == b"\n"


def test_load_invalid_schema(project):
    patch_settings = patch.object(project, "load_settings")
    patch_schema = patch.object(
        project, "load_schema", side_effect=SpecValidationError("")
    )
    with patch_settings as mock_settings, patch_schema as mock_schema, pytest.raises(
        InvalidProjectError
    ) as excinfo:
        project.load()

    mock_settings.assert_called_once_with()
    mock_schema.assert_called_once_with()

    assert "invalid" in str(excinfo.value)


def test_load_module_project_succeeds(project, tmp_path_factory):
    project.artifact_type = "MODULE"
    project.type_name = "Unit::Test::Malik::MODULE"
    project.root = tmp_path_factory.mktemp("load_module_test")
    os.mkdir(os.path.join(project.root, "fragments"))
    copyfile(
        os.path.join(
            os.path.dirname(__file__),
            "data/sample_fragments/fragments/valid_fragment.json",
        ),
        os.path.join(project.root, "fragments/valid_fragment.json"),
    )
    patch_load_settings = patch.object(
        project, "load_settings", return_value={"artifact_type": "MODULE"}
    )

    assert not os.path.exists(os.path.join(project.root, "schema.json"))
    with patch_load_settings:
        project.load()
    assert os.path.exists(os.path.join(project.root, "schema.json"))


def test_load_resource_succeeds(project):
    project.artifact_type = "Resource"
    project.type_name = "Unit::Test::Resource"
    patch_load_settings = patch.object(
        project, "load_settings", return_value={"artifact_type": "RESOURCE"}
    )
    project._write_example_schema()
    with patch_load_settings:
        project.load()


def test_load_module_project_with_invalid_fragments(project):
    project.artifact_type = "MODULE"
    project.type_name = "Unit::Test::Malik::MODULE"
    patch_load_settings = patch.object(
        project, "load_settings", return_value={"artifact_type": "MODULE"}
    )
    patch_validate = patch.object(
        project, "_validate_fragments", side_effect=FragmentValidationError
    )
    with patch_load_settings, patch_validate, pytest.raises(InvalidProjectError):
        project.load()


def test_schema_not_found(project):
    patch_settings = patch.object(project, "load_settings")
    patch_schema = patch.object(project, "load_schema", side_effect=FileNotFoundError)
    with patch_settings as mock_settings, patch_schema as mock_schema, pytest.raises(
        InvalidProjectError
    ) as excinfo:
        project.load()

    mock_settings.assert_called_once_with()
    mock_schema.assert_called_once_with()

    assert "not found" in str(excinfo.value)


def test_settings_not_found(project):
    patch_settings = patch.object(
        project, "load_settings", side_effect=FileNotFoundError
    )
    patch_schema = patch.object(project, "load_schema")

    with patch_settings as mock_settings, patch_schema as mock_schema, pytest.raises(
        InvalidProjectError
    ) as excinfo:
        project.load()

    mock_settings.assert_called_once_with()
    mock_schema.assert_not_called()

    assert "not found" in str(excinfo.value)
    assert "init" in str(excinfo.value)


def create_input_file(base):
    path = base / "inputs"
    os.mkdir(path, mode=0o777)

    path_create = base / CREATE_INPUTS_FILE
    with path_create.open("w", encoding="utf-8") as f:
        f.write("{}")

    path_update = base / UPDATE_INPUTS_FILE
    with path_update.open("w", encoding="utf-8") as f:
        f.write("{}")

    path_invalid = base / INVALID_INPUTS_FILE
    with path_invalid.open("w", encoding="utf-8") as f:
        f.write("{}")


# pylint: disable=too-many-arguments, too-many-locals
def test_submit_dry_run(project):
    project.type_name = TYPE_NAME
    project.runtime = RUNTIME
    project.language = LANGUAGE
    project.artifact_type = ARTIFACT_TYPE_RESOURCE
    zip_path = project.root / "test.zip"

    with project.schema_path.open("w", encoding="utf-8") as f:
        f.write(CONTENTS_UTF8)

    with project.overrides_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(empty_override()))

    create_input_file(project.root)

    project.write_settings()

    patch_plugin = patch.object(project, "_plugin", spec=LanguagePlugin)
    patch_upload = patch.object(project, "_upload", autospec=True)
    patch_path = patch("rpdk.core.project.Path", return_value=zip_path)
    patch_temp = patch("rpdk.core.project.TemporaryFile", autospec=True)

    # fmt: off
    # these context managers can't be wrapped by black, but it removes the \
    with patch_plugin as mock_plugin, patch_path as mock_path, \
            patch_temp as mock_temp, patch_upload as mock_upload:
        mock_plugin.get_plugin_information = MagicMock(return_value=PLUGIN_INFORMATION)

        project.submit(
            True,
            endpoint_url=ENDPOINT,
            region_name=REGION,
            role_arn=None,
            use_role=True,
            set_default=False
        )
    # fmt: on

    mock_temp.assert_not_called()
    mock_path.assert_called_with("{}.zip".format(project.hypenated_name))
    mock_plugin.package.assert_called_once_with(project, ANY)
    mock_upload.assert_not_called()

    with zipfile.ZipFile(zip_path, mode="r") as zip_file:
        assert set(zip_file.namelist()) == {
            SCHEMA_UPLOAD_FILENAME,
            SETTINGS_FILENAME,
            OVERRIDES_FILENAME,
            CREATE_INPUTS_FILE,
            INVALID_INPUTS_FILE,
            UPDATE_INPUTS_FILE,
            CFN_METADATA_FILENAME,
        }
        schema_contents = zip_file.read(SCHEMA_UPLOAD_FILENAME).decode("utf-8")
        assert schema_contents == CONTENTS_UTF8
        settings = json.loads(zip_file.read(SETTINGS_FILENAME).decode("utf-8"))
        assert settings["runtime"] == RUNTIME
        overrides = json.loads(zip_file.read(OVERRIDES_FILENAME).decode("utf-8"))
        assert "CREATE" in overrides
        # https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile.testzip
        input_create = json.loads(zip_file.read(CREATE_INPUTS_FILE).decode("utf-8"))
        assert input_create == {}
        input_invalid = json.loads(zip_file.read(INVALID_INPUTS_FILE).decode("utf-8"))
        assert input_invalid == {}
        input_update = json.loads(zip_file.read(UPDATE_INPUTS_FILE).decode("utf-8"))
        assert input_update == {}
        assert zip_file.testzip() is None
        metadata_info = json.loads(zip_file.read(CFN_METADATA_FILENAME).decode("utf-8"))
        assert "cli-version" in metadata_info
        assert "plugin-version" in metadata_info
        assert "plugin-tool-version" in metadata_info


def test_submit_dry_run_modules(project):
    project.type_name = MODULE_TYPE_NAME
    project.runtime = RUNTIME
    project.language = LANGUAGE
    project.artifact_type = ARTIFACT_TYPE_MODULE
    project.fragment_dir = project.root / "fragments"
    zip_path = project.root / "test.zip"
    schema_path = project.root / "schema.json"
    fragment_path = project.root / "fragments" / "fragment.json"

    with project.schema_path.open("w", encoding="utf-8") as f:
        f.write(CONTENTS_UTF8)

    with schema_path.open("w", encoding="utf-8") as f:
        f.write(CONTENTS_UTF8)

    if not os.path.exists(project.root / "fragments"):
        os.mkdir(project.root / "fragments")

    with fragment_path.open("w", encoding="utf-8") as f:
        f.write(CONTENTS_UTF8)

    with project.overrides_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(empty_override()))

    project.write_settings()

    patch_plugin = patch.object(project, "_plugin", spec=LanguagePlugin)
    patch_upload = patch.object(project, "_upload", autospec=True)
    patch_path = patch("rpdk.core.project.Path", return_value=zip_path)
    patch_temp = patch("rpdk.core.project.TemporaryFile", autospec=True)

    # fmt: off
    # these context managers can't be wrapped by black, but it removes the \
    with patch_plugin as mock_plugin, patch_path as mock_path, \
            patch_temp as mock_temp, patch_upload as mock_upload:
        project.submit(
            True,
            endpoint_url=ENDPOINT,
            region_name=REGION,
            role_arn=None,
            use_role=True,
            set_default=False
        )
    # fmt: on

    mock_temp.assert_not_called()
    mock_path.assert_called_with("{}.zip".format(project.hypenated_name))
    mock_plugin.package.assert_not_called()
    mock_upload.assert_not_called()

    fragment_file_name = "fragments/fragment.json"

    with zipfile.ZipFile(zip_path, mode="r") as zip_file:
        assert set(zip_file.namelist()) == {
            fragment_file_name,
            SCHEMA_UPLOAD_FILENAME,
            SETTINGS_FILENAME,
            OVERRIDES_FILENAME,
        }
        schema_contents = zip_file.read(SCHEMA_UPLOAD_FILENAME).decode("utf-8")
        assert schema_contents == CONTENTS_UTF8
        overrides = json.loads(zip_file.read(OVERRIDES_FILENAME).decode("utf-8"))
        assert "CREATE" in overrides
        # https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile.testzip
        assert zip_file.testzip() is None


def test_submit_live_run(project):
    project.type_name = TYPE_NAME
    project.runtime = RUNTIME
    project.language = LANGUAGE
    project.artifact_type = ARTIFACT_TYPE_RESOURCE

    with project.schema_path.open("w", encoding="utf-8") as f:
        f.write(CONTENTS_UTF8)

    project.write_settings()

    temp_file = UnclosingBytesIO()

    patch_plugin = patch.object(project, "_plugin", spec=LanguagePlugin)
    patch_upload = patch.object(project, "_upload", autospec=True)
    patch_path = patch("rpdk.core.project.Path", autospec=True)
    patch_temp = patch("rpdk.core.project.TemporaryFile", return_value=temp_file)

    # fmt: off
    # these context managers can't be wrapped by black, but it removes the \
    with patch_plugin as mock_plugin, patch_path as mock_path, \
            patch_temp as mock_temp, patch_upload as mock_upload:
        project.submit(
            False,
            endpoint_url=ENDPOINT,
            region_name=REGION,
            role_arn=None,
            use_role=True,
            set_default=True
        )
    # fmt: on

    mock_path.assert_not_called()
    mock_temp.assert_called_once_with("w+b")
    mock_plugin.package.assert_called_once_with(project, ANY)

    # zip file construction is tested by the dry-run test

    assert temp_file.tell() == 0  # file was rewound before upload
    mock_upload.assert_called_once_with(
        temp_file,
        region_name=REGION,
        endpoint_url=ENDPOINT,
        role_arn=None,
        use_role=True,
        set_default=True,
    )

    assert temp_file._was_closed
    temp_file._close()


def test_submit_live_run_for_module(project):
    project.type_name = MODULE_TYPE_NAME
    project.runtime = RUNTIME
    project.language = LANGUAGE
    project.artifact_type = ARTIFACT_TYPE_MODULE

    with project.schema_path.open("w", encoding="utf-8") as f:
        f.write(CONTENTS_UTF8)

    project.write_settings()

    temp_file = UnclosingBytesIO()

    patch_plugin = patch.object(project, "_plugin", spec=LanguagePlugin)
    patch_path = patch("rpdk.core.project.Path", autospec=True)
    patch_temp = patch("rpdk.core.project.TemporaryFile", return_value=temp_file)

    # fmt: off
    # these context managers can't be wrapped by black, but it removes the \
    with patch_plugin as mock_plugin, patch_path as mock_path, \
            patch_temp as mock_temp, \
            pytest.raises(InternalError):
        project.submit(
            False,
            endpoint_url=ENDPOINT,
            region_name=REGION,
            role_arn=None,
            use_role=True,
            set_default=True
        )
    # fmt: on

    mock_path.assert_not_called()
    mock_temp.assert_called_once_with("w+b")
    mock_plugin.package.assert_not_called()
    temp_file._close()


def test__upload_good_path_create_role_and_set_default(project):
    project.type_name = TYPE_NAME
    project.artifact_type = ARTIFACT_TYPE_RESOURCE
    project.schema = {"handlers": {}}

    mock_cfn_client = MagicMock(spec=["register_type"])
    mock_cfn_client.register_type.return_value = {"RegistrationToken": "foo"}
    fileobj = object()

    patch_sdk = patch("rpdk.core.project.create_sdk_session", autospec=True)
    patch_uploader = patch.object(Uploader, "upload", return_value="url")
    patch_exec_role_arn = patch.object(
        Uploader, "create_or_update_role", return_value="some-execution-role-arn"
    )
    patch_logging_role_arn = patch.object(
        Uploader, "get_log_delivery_role_arn", return_value="some-log-role-arn"
    )
    patch_uuid = patch("rpdk.core.project.uuid4", autospec=True, return_value="foo")
    patch_wait = patch.object(project, "_wait_for_registration", autospec=True)

    with patch_sdk as mock_sdk, patch_uploader as mock_upload_method, patch_logging_role_arn as mock_role_arn_method, patch_exec_role_arn as mock_exec_role_method:  # noqa: B950 as it conflicts with formatting rules # pylint: disable=C0301
        mock_sdk.return_value.client.side_effect = [mock_cfn_client, MagicMock()]
        with patch_uuid as mock_uuid, patch_wait as mock_wait:
            project._upload(
                fileobj,
                endpoint_url=None,
                region_name=None,
                role_arn=None,
                use_role=True,
                set_default=True,
            )

    mock_sdk.assert_called_once_with(None)
    mock_exec_role_method.assert_called_once_with(
        project.root / "resource-role.yaml", project.hypenated_name
    )
    mock_upload_method.assert_called_once_with(project.hypenated_name, fileobj)
    mock_role_arn_method.assert_called_once_with()
    mock_uuid.assert_called_once_with()
    mock_cfn_client.register_type.assert_called_once_with(
        Type="RESOURCE",
        TypeName=project.type_name,
        SchemaHandlerPackage="url",
        ClientRequestToken=mock_uuid.return_value,
        LoggingConfig={
            "LogRoleArn": "some-log-role-arn",
            "LogGroupName": "aws-color-red-logs",
        },
        ExecutionRoleArn="some-execution-role-arn",
    )
    mock_wait.assert_called_once_with(mock_cfn_client, "foo", True)


@pytest.mark.parametrize(
    ("use_role,expected_additional_args"),
    [(True, {"ExecutionRoleArn": "someArn"}), (False, {})],
)
def test__upload_good_path_skip_role_creation(
    project, use_role, expected_additional_args
):
    project.type_name = TYPE_NAME
    project.artifact_type = ARTIFACT_TYPE_RESOURCE
    project.schema = {"handlers": {}}

    mock_cfn_client = MagicMock(spec=["register_type"])
    fileobj = object()
    mock_cfn_client.register_type.return_value = {"RegistrationToken": "foo"}

    patch_sdk = patch("rpdk.core.project.create_sdk_session", autospec=True)
    patch_uploader = patch.object(Uploader, "upload", return_value="url")
    patch_logging_role_arn = patch.object(
        Uploader, "get_log_delivery_role_arn", return_value="some-log-role-arn"
    )
    patch_uuid = patch("rpdk.core.project.uuid4", autospec=True, return_value="foo")
    patch_wait = patch.object(project, "_wait_for_registration", autospec=True)

    with patch_sdk as mock_sdk, patch_uploader as mock_upload_method, patch_logging_role_arn as mock_role_arn_method:  # noqa: B950 as it conflicts with formatting rules # pylint: disable=C0301
        mock_sdk.return_value.client.side_effect = [mock_cfn_client, MagicMock()]
        with patch_uuid as mock_uuid, patch_wait as mock_wait:
            project._upload(
                fileobj,
                endpoint_url=None,
                region_name=None,
                role_arn="someArn",
                use_role=use_role,
                set_default=True,
            )

    mock_sdk.assert_called_once_with(None)
    mock_upload_method.assert_called_once_with(project.hypenated_name, fileobj)
    mock_role_arn_method.assert_called_once_with()
    mock_uuid.assert_called_once_with()
    mock_wait.assert_called_once_with(mock_cfn_client, "foo", True)

    mock_cfn_client.register_type.assert_called_once_with(
        Type="RESOURCE",
        TypeName=project.type_name,
        SchemaHandlerPackage="url",
        ClientRequestToken=mock_uuid.return_value,
        LoggingConfig={
            "LogRoleArn": "some-log-role-arn",
            "LogGroupName": "aws-color-red-logs",
        },
        **expected_additional_args,
    )


def test__upload_clienterror(project):
    project.type_name = TYPE_NAME
    project.artifact_type = ARTIFACT_TYPE_RESOURCE
    project.schema = {}

    mock_cfn_client = MagicMock(spec=["register_type"])
    mock_cfn_client.register_type.side_effect = ClientError(
        BLANK_CLIENT_ERROR, "RegisterType"
    )
    fileobj = object()

    patch_sdk = patch("rpdk.core.project.create_sdk_session", autospec=True)
    patch_uploader = patch.object(Uploader, "upload", return_value="url")
    patch_role_arn = patch.object(
        Uploader, "get_log_delivery_role_arn", return_value="some-log-role-arn"
    )
    patch_uuid = patch("rpdk.core.project.uuid4", autospec=True, return_value="foo")

    with patch_sdk as mock_sdk, patch_uploader as mock_upload_method, patch_role_arn as mock_role_arn_method:  # noqa: B950 as it conflicts with formatting rules # pylint: disable=C0301
        mock_session = mock_sdk.return_value
        mock_session.client.side_effect = [mock_cfn_client, MagicMock()]
        with patch_uuid as mock_uuid, pytest.raises(DownstreamError):
            project._upload(
                fileobj,
                endpoint_url=None,
                region_name=None,
                role_arn=None,
                use_role=False,
                set_default=True,
            )

    mock_sdk.assert_called_once_with(None)
    mock_upload_method.assert_called_once_with(project.hypenated_name, fileobj)
    mock_role_arn_method.assert_called_once_with()
    mock_uuid.assert_called_once_with()
    mock_cfn_client.register_type.assert_called_once_with(
        Type="RESOURCE",
        TypeName=project.type_name,
        SchemaHandlerPackage="url",
        ClientRequestToken=mock_uuid.return_value,
        LoggingConfig={
            "LogRoleArn": "some-log-role-arn",
            "LogGroupName": "aws-color-red-logs",
        },
    )


def test__upload_clienterror_module(project):
    project.type_name = MODULE_TYPE_NAME
    project.artifact_type = ARTIFACT_TYPE_MODULE
    project.schema = {}

    mock_cfn_client = MagicMock(spec=["register_type"])
    mock_cfn_client.register_type.side_effect = ClientError(
        BLANK_CLIENT_ERROR, "RegisterType"
    )
    fileobj = object()

    patch_sdk = patch("rpdk.core.project.create_sdk_session", autospec=True)
    patch_uploader = patch.object(Uploader, "upload", return_value="url")
    patch_role_arn = patch.object(
        Uploader, "get_log_delivery_role_arn", return_value="some-log-role-arn"
    )
    patch_uuid = patch("rpdk.core.project.uuid4", autospec=True, return_value="foo")

    with patch_sdk as mock_sdk, patch_uploader as mock_upload_method, patch_role_arn as mock_role_arn_method:  # noqa: B950 as it conflicts with formatting rules # pylint: disable=C0301
        mock_session = mock_sdk.return_value
        mock_session.client.side_effect = [mock_cfn_client, MagicMock()]
        with patch_uuid as mock_uuid, pytest.raises(DownstreamError):
            project._upload(
                fileobj,
                endpoint_url=None,
                region_name=None,
                role_arn=None,
                use_role=False,
                set_default=True,
            )

    mock_sdk.assert_called_once_with(None)
    mock_upload_method.assert_called_once_with(project.hypenated_name, fileobj)
    mock_role_arn_method.assert_called_once_with()
    mock_uuid.assert_called_once_with()
    mock_cfn_client.register_type.assert_called_once_with(
        Type="MODULE",
        TypeName=project.type_name,
        SchemaHandlerPackage="url",
        ClientRequestToken=mock_uuid.return_value,
        LoggingConfig={
            "LogRoleArn": "some-log-role-arn",
            "LogGroupName": "aws-color-red-module-logs",
        },
    )


def test__wait_for_registration_set_default(project):
    mock_cfn_client = MagicMock(
        spec=["describe_type_registration", "set_type_default_version", "get_waiter"]
    )
    mock_cfn_client.describe_type_registration.return_value = (
        DESCRIBE_TYPE_COMPLETE_RETURN
    )
    mock_waiter = MagicMock(spec=["wait"])
    mock_cfn_client.get_waiter.return_value = mock_waiter

    project._wait_for_registration(mock_cfn_client, REGISTRATION_TOKEN, True)

    mock_cfn_client.describe_type_registration.assert_called_once_with(
        RegistrationToken=REGISTRATION_TOKEN
    )
    mock_cfn_client.set_type_default_version.assert_called_once_with(
        Arn=TYPE_VERSION_ARN
    )
    mock_waiter.wait.assert_called_once_with(RegistrationToken=REGISTRATION_TOKEN)


def test__wait_for_registration_set_default_fails(project):
    mock_cfn_client = MagicMock(
        spec=["describe_type_registration", "set_type_default_version", "get_waiter"]
    )
    mock_cfn_client.describe_type_registration.return_value = (
        DESCRIBE_TYPE_COMPLETE_RETURN
    )
    mock_cfn_client.set_type_default_version.side_effect = ClientError(
        BLANK_CLIENT_ERROR, "SetTypeDefaultVersion"
    )
    mock_waiter = MagicMock(spec=["wait"])
    mock_cfn_client.get_waiter.return_value = mock_waiter

    with pytest.raises(DownstreamError):
        project._wait_for_registration(mock_cfn_client, REGISTRATION_TOKEN, True)

    mock_cfn_client.describe_type_registration.assert_called_once_with(
        RegistrationToken=REGISTRATION_TOKEN
    )
    mock_cfn_client.set_type_default_version.assert_called_once_with(
        Arn=TYPE_VERSION_ARN
    )
    mock_waiter.wait.assert_called_once_with(RegistrationToken=REGISTRATION_TOKEN)


def test__wait_for_registration_no_set_default(project):
    mock_cfn_client = MagicMock(
        spec=["describe_type_registration", "set_type_default_version", "get_waiter"]
    )
    mock_cfn_client.describe_type_registration.return_value = (
        DESCRIBE_TYPE_COMPLETE_RETURN
    )
    mock_waiter = MagicMock(spec=["wait"])
    mock_cfn_client.get_waiter.return_value = mock_waiter

    project._wait_for_registration(mock_cfn_client, REGISTRATION_TOKEN, False)

    mock_cfn_client.describe_type_registration.assert_called_once_with(
        RegistrationToken=REGISTRATION_TOKEN
    )
    mock_cfn_client.set_type_default_version.assert_not_called()
    mock_waiter.wait.assert_called_once_with(RegistrationToken=REGISTRATION_TOKEN)


def test__wait_for_registration_waiter_fails(project):
    mock_cfn_client = MagicMock(
        spec=["describe_type_registration", "set_type_default_version", "get_waiter"]
    )
    mock_cfn_client.describe_type_registration.return_value = (
        DESCRIBE_TYPE_FAILED_RETURN
    )
    mock_waiter = MagicMock(spec=["wait"])
    mock_waiter.wait.side_effect = WaiterError(
        "TypeRegistrationComplete",
        "Waiter encountered a terminal failure state",
        DESCRIBE_TYPE_FAILED_RETURN,
    )
    mock_cfn_client.get_waiter.return_value = mock_waiter

    with pytest.raises(DownstreamError):
        project._wait_for_registration(mock_cfn_client, REGISTRATION_TOKEN, True)

    mock_cfn_client.describe_type_registration.assert_called_once_with(
        RegistrationToken=REGISTRATION_TOKEN
    )
    mock_cfn_client.set_type_default_version.assert_not_called()
    mock_waiter.wait.assert_called_once_with(RegistrationToken=REGISTRATION_TOKEN)


def test__wait_for_registration_waiter_fails_describe_fails(project):
    mock_cfn_client = MagicMock(
        spec=["describe_type_registration", "set_type_default_version", "get_waiter"]
    )
    mock_cfn_client.describe_type_registration.side_effect = ClientError(
        BLANK_CLIENT_ERROR, "DescribeTypeRegistration"
    )
    mock_waiter = MagicMock(spec=["wait"])
    mock_waiter.wait.side_effect = WaiterError(
        "TypeRegistrationComplete",
        "Waiter encountered a terminal failure state",
        DESCRIBE_TYPE_FAILED_RETURN,
    )

    mock_cfn_client.get_waiter.return_value = mock_waiter

    with pytest.raises(DownstreamError):
        project._wait_for_registration(mock_cfn_client, REGISTRATION_TOKEN, False)

    mock_cfn_client.describe_type_registration.assert_called_once_with(
        RegistrationToken=REGISTRATION_TOKEN
    )
    mock_cfn_client.set_type_default_version.assert_not_called()
    mock_waiter.wait.assert_called_once_with(RegistrationToken=REGISTRATION_TOKEN)


def test__write_settings_invalid_runtime(project):
    project.runtime = "foo"
    project.language = LANGUAGE

    with pytest.raises(InternalError):
        project.write_settings()


@pytest.mark.parametrize(
    "docs_schema",
    (
        {},
        {"primaryIdentifier": ["/properties/Id1", "/properties/Id1"]},
        {"primaryIdentifier": ["/properties/Nested/Id1"]},
    ),
)
def test__get_docs_primary_identifier_bad_path(docs_schema):
    ref = Project._get_docs_primary_identifier(docs_schema)
    assert ref is None


def test__get_docs_primary_identifier_good_path():
    ref = Project._get_docs_primary_identifier(
        {"primaryIdentifier": ["/properties/Id1"]}
    )
    assert ref == "Id1"


def test__get_docs_gettable_atts_empty():
    getatt = Project._get_docs_gettable_atts({})
    assert getatt == []


@pytest.mark.parametrize(
    "docs_schema",
    (
        {"readOnlyProperties": ["/properties/Id2"]},
        {"properties": {}, "readOnlyProperties": ["/properties/Id2"]},
        {"properties": {"Id2": {}}, "readOnlyProperties": ["/properties/Id2"]},
    ),
)
def test__get_docs_gettable_atts_bad_path(docs_schema):
    getatt = Project._get_docs_gettable_atts(docs_schema)
    assert getatt == [
        {"name": "Id2", "description": "Returns the <code>Id2</code> value."}
    ]


def test__get_docs_gettable_atts_good_path():
    getatt = Project._get_docs_gettable_atts(
        {
            "properties": {"Id2": {"description": "foo"}},
            "readOnlyProperties": ["/properties/Id2"],
        }
    )
    assert getatt == [{"name": "Id2", "description": "foo"}]


def test_generate_image_build_config(project):
    project.schema = {}
    mock_plugin = MagicMock(spec=["generate_image_build_config"])
    with patch.object(project, "_plugin", mock_plugin):
        project.generate_image_build_config()
    mock_plugin.generate_image_build_config.assert_called_once()


def test_generate_image_build_config_plugin_not_supported(project):
    project.schema = {}
    mock_plugin = MagicMock(spec=[])
    with patch.object(project, "_plugin", mock_plugin):
        try:
            project.generate_image_build_config()
        except InvalidProjectError:
            pass


def test__write_settings_null_executable_entrypoint(project):
    project.type_name = TYPE_NAME
    project.artifact_type = ARTIFACT_TYPE_RESOURCE
    project.runtime = RUNTIME
    project.language = LANGUAGE
    project.executable_entrypoint = None

    project.write_settings()
    with project.settings_path.open("r", encoding="utf-8") as f:
        settings = json.load(f)
        assert "executableEntrypoint" not in settings


def test__write_settings_nonnull_executable_entrypoint(project):
    project.type_name = TYPE_NAME
    project.artifact_type = ARTIFACT_TYPE_RESOURCE
    project.runtime = RUNTIME
    project.language = LANGUAGE
    project.executable_entrypoint = "executable_entrypoint"

    project.write_settings()
    with project.settings_path.open("r", encoding="utf-8") as f:
        settings = json.load(f)
        assert "executableEntrypoint" in settings
        assert settings["executableEntrypoint"] == "executable_entrypoint"
