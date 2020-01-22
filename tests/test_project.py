# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,useless-super-delegation,protected-access
import json
import os
import random
import string
import zipfile
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest
import yaml
from botocore.exceptions import ClientError, WaiterError

from rpdk.core.exceptions import (
    DownstreamError,
    InternalError,
    InvalidProjectError,
    SpecValidationError,
)
from rpdk.core.plugin_base import LanguagePlugin
from rpdk.core.project import (
    LAMBDA_RUNTIMES,
    OVERRIDES_FILENAME,
    SCHEMA_UPLOAD_FILENAME,
    SETTINGS_FILENAME,
    Project,
)
from rpdk.core.test import empty_override
from rpdk.core.upload import Uploader

from .utils import CONTENTS_UTF8, UnclosingBytesIO

LANGUAGE = "BQHDBC"
TYPE_NAME = "AWS::Color::Red"
REGION = "us-east-1"
ENDPOINT = "cloudformation.beta.com"
RUNTIME = random.choice(list(LAMBDA_RUNTIMES))
BLANK_CLIENT_ERROR = {"Error": {"Code": "", "Message": ""}}

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


def test_load_settings_valid_json(project):
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
    assert project._plugin is plugin
    assert project.settings == {}


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
    path = Path(tmpdir.join("test")).resolve()

    with path.open("w", encoding="utf-8") as f:
        f.write(CONTENTS_UTF8)

    with patch.object(project, "overwrite_enabled", False):
        project.safewrite(path, CONTENTS_UTF8)

    last_record = caplog.records[-1]
    assert last_record.levelname == "WARNING"
    assert str(path) in last_record.message


def test_generate_no_handlers(project):
    project.schema = {}
    mock_plugin = MagicMock(spec=["generate"])
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
    mock_plugin.generate.assert_called_once_with(project)


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


def test_init(project):
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

    # ends with newline
    with project.schema_path.open("rb") as f:
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


def test_submit_dry_run(project):
    project.type_name = TYPE_NAME
    project.runtime = RUNTIME
    zip_path = project.root / "test.zip"

    with project.schema_path.open("w", encoding="utf-8") as f:
        f.write(CONTENTS_UTF8)

    with project.overrides_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(empty_override()))
    project._write_settings("foo")

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
    mock_path.assert_called_once_with("{}.zip".format(project.hypenated_name))
    mock_plugin.package.assert_called_once_with(project, ANY)
    mock_upload.assert_not_called()

    with zipfile.ZipFile(zip_path, mode="r") as zip_file:
        assert set(zip_file.namelist()) == {
            SCHEMA_UPLOAD_FILENAME,
            SETTINGS_FILENAME,
            OVERRIDES_FILENAME,
        }
        schema_contents = zip_file.read(SCHEMA_UPLOAD_FILENAME).decode("utf-8")
        assert schema_contents == CONTENTS_UTF8
        settings = json.loads(zip_file.read(SETTINGS_FILENAME).decode("utf-8"))
        assert settings["runtime"] == RUNTIME
        overrides = json.loads(zip_file.read(OVERRIDES_FILENAME).decode("utf-8"))
        assert "CREATE" in overrides
        # https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile.testzip
        assert zip_file.testzip() is None


def test_submit_live_run(project):
    project.type_name = TYPE_NAME
    project.runtime = RUNTIME

    with project.schema_path.open("w", encoding="utf-8") as f:
        f.write(CONTENTS_UTF8)

    project._write_settings("foo")

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


def test__upload_good_path_create_role_and_set_default(project):
    project.type_name = TYPE_NAME
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
        **expected_additional_args
    )


def test__upload_clienterror(project):
    project.type_name = TYPE_NAME
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
    with pytest.raises(InternalError):
        project._write_settings("foo")
