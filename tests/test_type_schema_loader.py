# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,useless-super-delegation,protected-access
import json
import unittest
from io import BytesIO
from unittest.mock import Mock, call, mock_open, patch

import pytest
from botocore.exceptions import ClientError
from requests import HTTPError

from rpdk.core.exceptions import DownstreamError, InvalidTypeSchemaError
from rpdk.core.type_schema_loader import TypeSchemaLoader, is_valid_type_schema_uri


def get_test_schema(type_name):
    return {
        "typeName": type_name,
        "description": "test schema",
        "properties": {"foo": {"type": "string"}},
        "primaryIdentifier": ["/properties/foo"],
        "additionalProperties": False,
    }


TEST_TARGET_TYPE_NAME = "AWS::Test::Target"
TEST_TARGET_SCHEMA = get_test_schema(TEST_TARGET_TYPE_NAME)
TEST_TARGET_SCHEMA_JSON = json.dumps(TEST_TARGET_SCHEMA)
TEST_TARGET_SCHEMA_JSON_ARRAY = json.dumps([TEST_TARGET_SCHEMA])
MULTIPLE_TEST_TARGET_SCHEMAS = [
    get_test_schema("AWS::Other::Target"),
    get_test_schema("MyCompany::Test::Target"),
    get_test_schema("Another::Test::Target"),
]
MULTIPLE_TEST_TARGET_SCHEMAS_JSON = json.dumps(MULTIPLE_TEST_TARGET_SCHEMAS)

TEST_TARGET_SCHEMA_BUCKET = "TestTargetSchemaBucket"
TEST_TARGET_SCHEMA_KEY = "test-target-schema.json"
TEST_TARGET_SCHEMA_FILE_PATH = f"/files/{TEST_TARGET_SCHEMA_KEY}"
TEST_TARGET_SCHEMA_FILE_URI = f"file://{TEST_TARGET_SCHEMA_FILE_PATH}"  # noqa: E231
TEST_S3_TARGET_SCHEMA_URI = (
    f"s3://{TEST_TARGET_SCHEMA_BUCKET}/{TEST_TARGET_SCHEMA_KEY}"  # noqa: E231
)
TEST_HTTPS_TARGET_SCHEMA_URI = f"https://{TEST_TARGET_SCHEMA_BUCKET}.s3.us-west-2.amazonaws.com/{TEST_TARGET_SCHEMA_KEY}"  # noqa: E231


# pylint: disable=C0103
def assert_dict_equals(d1, d2):
    unittest.TestCase().assertDictEqual(d1, d2)


def get_test_type_info(type_name, visibility, provisioning_type):
    return {
        "TypeName": type_name,
        "TargetName": type_name,
        "TargetType": "RESOURCE",
        "Type": "RESOURCE",
        "Arn": (
            f'arn:aws:cloudformation:us-east-1:12345678902:type:resource:{type_name.replace("::", "-")}'  # noqa: E231
        ),
        "IsDefaultVersion": True,
        "Description": "Test Schema",
        "ProvisioningType": provisioning_type,
        "DeprecatedStatus": "LIVE",
        "Visibility": visibility,
        "Schema": get_test_schema(type_name),
    }


def describe_type_result(type_name, visibility, provisioning_type):
    return {
        "Arn": (
            f'arn:aws:cloudformation:us-east-1:12345678902:type:resource:{type_name.replace("::", "-")}'  # noqa: E231
        ),
        "Type": "RESOURCE",
        "TypeName": type_name,
        "IsDefaultVersion": True,
        "Description": "Test Schema",
        "ProvisioningType": provisioning_type,
        "DeprecatedStatus": "LIVE",
        "Visibility": visibility,
        "Schema": json.dumps(get_test_schema(type_name)),
    }


@pytest.fixture
def loader():
    return TypeSchemaLoader(Mock(), Mock())


@pytest.fixture
def local_loader():
    return TypeSchemaLoader(Mock(), Mock(), local_only=True)


def test_load_type_info(loader):
    remote_types = {
        t[0]: t
        for t in [
            ("AWS::Test::Target", "PUBLIC", "FULLY_MUTABLE"),
            ("AWS::Other::Target", "PRIVATE", "IMMUTABLE"),
            ("MyCompany::Test::Target", "PUBLIC", "NON_PROVISIONABLE"),
            ("Another::Test::Target", "PUBLIC", "IMMUTABLE"),
        ]
    }
    local_types = {
        t[0]: t
        for t in [
            ("MyFile::Hook::Target", "PRIVATE", "NON_PROVISIONABLE"),
            ("MyHttp::Hook::Target", "PUBLIC", "NON_PROVISIONABLE"),
            ("MyS3::Hook::Target", "PUBLIC", "IMMUTABLE"),
        ]
    }

    local_info = {
        type_name: get_test_type_info(type_name, visibility, provisioning_type)
        for type_name, visibility, provisioning_type in local_types.values()
    }
    loaded_schemas = {
        target["TypeName"]: target["Schema"] for target in local_info.values()
    }

    local_info["MyFile::Hook::Target"].pop("Schema")

    test_types = {**remote_types, **local_types}

    def mock_describe_type(**kwargs):
        type_name, visibility, provisioning_type = test_types[kwargs["TypeName"]]
        return describe_type_result(type_name, visibility, provisioning_type)

    loader.cfn_client.describe_type.side_effect = mock_describe_type

    type_info = loader.load_type_info(test_types.keys(), loaded_schemas, local_info)

    expected = {
        type_name: {
            **get_test_type_info(type_name, visibility, provisioning_type),
            "IsCfnRegistrySupportedType": True,
            "SchemaFileAvailable": True,
        }
        for type_name, visibility, provisioning_type in test_types.values()
    }

    assert type_info == expected
    loader.cfn_client.describe_type.assert_has_calls(
        calls=[
            call(TypeName="AWS::Test::Target", Type="RESOURCE"),
            call(TypeName="AWS::Other::Target", Type="RESOURCE"),
            call(TypeName="MyCompany::Test::Target", Type="RESOURCE"),
            call(TypeName="Another::Test::Target", Type="RESOURCE"),
        ],
        any_order=True,
    )


def test_load_remote_type_info(loader):
    test_types = {
        t[0]: t
        for t in [
            ("AWS::Test::Target", "PUBLIC", "FULLY_MUTABLE"),
            ("AWS::Other::Target", "PRIVATE", "IMMUTABLE"),
            ("MyCompany::Test::Target", "PUBLIC", "NON_PROVISIONABLE"),
            ("Another::Test::Target", "PUBLIC", "IMMUTABLE"),
        ]
    }

    def mock_describe_type(**kwargs):
        type_name, visibility, provisioning_type = test_types[kwargs["TypeName"]]
        return describe_type_result(type_name, visibility, provisioning_type)

    loader.cfn_client.describe_type.side_effect = mock_describe_type

    type_info = loader.load_type_info(test_types.keys())

    expected = {
        type_name: {
            **get_test_type_info(type_name, visibility, provisioning_type),
            "IsCfnRegistrySupportedType": True,
            "SchemaFileAvailable": True,
        }
        for type_name, visibility, provisioning_type in test_types.values()
    }

    assert type_info == expected

    loader.cfn_client.describe_type.assert_has_calls(
        calls=[
            call(TypeName="AWS::Test::Target", Type="RESOURCE"),
            call(TypeName="AWS::Other::Target", Type="RESOURCE"),
            call(TypeName="MyCompany::Test::Target", Type="RESOURCE"),
            call(TypeName="Another::Test::Target", Type="RESOURCE"),
        ],
        any_order=True,
    )


def test_load_local_type_info(loader):
    test_types = {
        t[0]: t
        for t in [
            ("MyFile::Hook::Target", "PRIVATE", "NON_PROVISIONABLE"),
            ("MyHttp::Hook::Target", "PUBLIC", "NON_PROVISIONABLE"),
            ("MyS3::Hook::Target", "PUBLIC", "IMMUTABLE"),
        ]
    }

    local_info = {
        type_name: get_test_type_info(type_name, visibility, provisioning_type)
        for type_name, visibility, provisioning_type in test_types.values()
    }
    loaded_schemas = {
        target["TypeName"]: target["Schema"] for target in local_info.values()
    }

    def mock_describe_type(**kwargs):
        type_name, visibility, provisioning_type = test_types[kwargs["TypeName"]]
        return describe_type_result(type_name, visibility, provisioning_type)

    loader.cfn_client.describe_type.side_effect = mock_describe_type

    target_info = loader.load_type_info(test_types.keys(), loaded_schemas, local_info)

    expected = {
        type_name: {
            **get_test_type_info(type_name, visibility, provisioning_type),
            "IsCfnRegistrySupportedType": True,
            "SchemaFileAvailable": True,
        }
        for type_name, visibility, provisioning_type in test_types.values()
    }

    assert target_info == expected

    loader.cfn_client.describe_type.assert_not_called()


def test_load_type_info_missing_info(loader):
    remote_types = {
        t[0]: t
        for t in [
            ("AWS::Test::Target", "PUBLIC", "FULLY_MUTABLE"),
            ("AWS::Other::Target", "PRIVATE", "IMMUTABLE"),
            ("MyCompany::Test::Target", "PUBLIC", "NON_PROVISIONABLE"),
            ("Another::Test::Target", "PUBLIC", "IMMUTABLE"),
        ]
    }
    local_types = {
        t[0]: t
        for t in [
            ("MyFile::Hook::Target", "PRIVATE", "NON_PROVISIONABLE"),
            ("MyHttp::Hook::Target", "PUBLIC", "NON_PROVISIONABLE"),
            ("MyS3::Hook::Target", "PUBLIC", "IMMUTABLE"),
        ]
    }

    local_info = {
        type_name: get_test_type_info(type_name, visibility, provisioning_type)
        for type_name, visibility, provisioning_type in local_types.values()
    }
    loaded_schemas = {
        target["TypeName"]: target["Schema"] for target in local_info.values()
    }

    loaded_schemas.pop("MyFile::Hook::Target")

    test_types = {**remote_types, **local_types}

    def mock_describe_type(**kwargs):
        type_name, visibility, provisioning_type = test_types[kwargs["TypeName"]]
        return describe_type_result(type_name, visibility, provisioning_type)

    loader.cfn_client.describe_type.side_effect = mock_describe_type

    type_info = loader.load_type_info(test_types.keys(), loaded_schemas, local_info)

    expecting = {
        type_name: {
            **get_test_type_info(type_name, visibility, provisioning_type),
            "IsCfnRegistrySupportedType": True,
            "SchemaFileAvailable": True,
        }
        for type_name, visibility, provisioning_type in test_types.values()
    }
    assert type_info == expecting


def test_load_type_info_missing_schema(loader):
    remote_types = {
        t[0]: t
        for t in [
            ("AWS::Test::Target", "PUBLIC", "FULLY_MUTABLE"),
            ("AWS::Other::Target", "PRIVATE", "IMMUTABLE"),
            ("MyCompany::Test::Target", "PUBLIC", "NON_PROVISIONABLE"),
            ("Another::Test::Target", "PUBLIC", "IMMUTABLE"),
        ]
    }
    local_types = {
        t[0]: t
        for t in [
            ("MyFile::Hook::Target", "PRIVATE", "NON_PROVISIONABLE"),
            ("MyHttp::Hook::Target", "PUBLIC", "NON_PROVISIONABLE"),
            ("MyS3::Hook::Target", "PUBLIC", "IMMUTABLE"),
        ]
    }

    local_info = {
        type_name: get_test_type_info(type_name, visibility, provisioning_type)
        for type_name, visibility, provisioning_type in local_types.values()
    }
    loaded_schemas = {
        target["TypeName"]: target["Schema"] for target in local_info.values()
    }

    local_info["MyFile::Hook::Target"].pop("Schema")
    loaded_schemas.pop("MyFile::Hook::Target")

    test_types = {**remote_types, **local_types}

    def mock_describe_type(**kwargs):
        type_name, visibility, provisioning_type = test_types[kwargs["TypeName"]]
        return describe_type_result(type_name, visibility, provisioning_type)

    loader.cfn_client.describe_type.side_effect = mock_describe_type

    with pytest.raises(InvalidTypeSchemaError) as excinfo:
        loader.load_type_info(test_types.keys(), loaded_schemas, local_info)

    assert "No local schema provided for 'MyFile::Hook::Target' target type" in str(
        excinfo.value
    )


def test_load_local_type_info_missing_info(local_loader):
    remote_types = {
        t[0]: t
        for t in [
            ("AWS::Test::Target", "PUBLIC", "FULLY_MUTABLE"),
            ("AWS::Other::Target", "PRIVATE", "IMMUTABLE"),
            ("MyCompany::Test::Target", "PUBLIC", "NON_PROVISIONABLE"),
            ("Another::Test::Target", "PUBLIC", "IMMUTABLE"),
        ]
    }
    local_types = {
        t[0]: t
        for t in [
            ("MyFile::Hook::Target", "PRIVATE", "NON_PROVISIONABLE"),
            ("MyHttp::Hook::Target", "PUBLIC", "NON_PROVISIONABLE"),
            ("MyS3::Hook::Target", "PUBLIC", "IMMUTABLE"),
        ]
    }

    local_info = {
        type_name: get_test_type_info(type_name, visibility, provisioning_type)
        for type_name, visibility, provisioning_type in local_types.values()
    }
    loaded_schemas = {
        target["TypeName"]: target["Schema"] for target in local_info.values()
    }

    loaded_schemas.pop("MyFile::Hook::Target")

    test_types = {**remote_types, **local_types}

    with pytest.raises(InvalidTypeSchemaError) as excinfo:
        local_loader.load_type_info(test_types.keys(), loaded_schemas, local_info)

    assert (
        "Local type schema or 'target-info.json' are required to load local type info"
        in str(excinfo.value)
    )


def test_load_type_info_invalid_local_schemas(loader):
    type_names = ["AWS::Test::Target", "AWS::Test::DifferentTarget"]
    with pytest.raises(InvalidTypeSchemaError) as excinfo:
        loader.load_type_info(type_names, local_schemas=0)

    assert (
        "Local Schemas must be either list of schemas to load or mapping of type names"
        " to schemas" in str(excinfo.value)
    )


@pytest.mark.parametrize(
    "local_schemas,expected_schemas",
    [
        (None, {}),
        (
            {schema["typeName"]: schema for schema in MULTIPLE_TEST_TARGET_SCHEMAS},
            {schema["typeName"]: schema for schema in MULTIPLE_TEST_TARGET_SCHEMAS},
        ),
        (
            MULTIPLE_TEST_TARGET_SCHEMAS,
            {schema["typeName"]: schema for schema in MULTIPLE_TEST_TARGET_SCHEMAS},
        ),
        (
            [json.dumps(ts) for ts in MULTIPLE_TEST_TARGET_SCHEMAS],
            {schema["typeName"]: schema for schema in MULTIPLE_TEST_TARGET_SCHEMAS},
        ),
        (
            MULTIPLE_TEST_TARGET_SCHEMAS_JSON,
            {schema["typeName"]: schema for schema in MULTIPLE_TEST_TARGET_SCHEMAS},
        ),
    ],
)
def test_validate_and_load_local_schemas(local_schemas, expected_schemas):
    loader = TypeSchemaLoader(Mock(), Mock())
    schemas = loader._validate_and_load_local_schemas(local_schemas)

    assert schemas == expected_schemas


# pylint: disable=too-many-locals
def test_load_type_schemas(loader):
    schemas_to_load = [
        TEST_TARGET_SCHEMA_JSON,
        MULTIPLE_TEST_TARGET_SCHEMAS_JSON,
        TEST_TARGET_SCHEMA_FILE_PATH,
        TEST_HTTPS_TARGET_SCHEMA_URI,
        TEST_S3_TARGET_SCHEMA_URI,
    ]

    # Load from JSON
    patch_load_json = patch.object(
        loader, "load_type_schema_from_json", wraps=loader.load_type_schema_from_json
    )

    # Load from File
    patch_file = patch(
        "builtins.open",
        mock_open(read_data=json.dumps(get_test_schema("MyFile::Hook::Target"))),
    )
    patch_path_is_file = patch(
        "rpdk.core.type_schema_loader.os.path.isfile",
        side_effect=lambda s: s == TEST_TARGET_SCHEMA_FILE_PATH,
    )
    patch_load_file = patch.object(
        loader, "load_type_schema_from_file", wraps=loader.load_type_schema_from_file
    )

    # Load from HTTP Request
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = json.dumps(get_test_schema("MyHttp::Hook::Target")).encode(
        "utf-8"
    )
    patch_get_request = patch(
        "rpdk.core.type_schema_loader.requests.get", return_value=mock_response
    )
    patch_get_from_url = patch.object(
        loader, "_get_type_schema_from_url", wraps=loader._get_type_schema_from_url
    )

    # Load from S3
    loader.s3_client.get_object.return_value = {
        "Body": BytesIO(
            json.dumps(get_test_schema("MyS3::Hook::Target")).encode("utf-8")
        )
    }
    patch_get_from_s3 = patch.object(
        loader, "_get_type_schema_from_s3", wraps=loader._get_type_schema_from_s3
    )

    # Formatting check makes this line too long which causes pylint to fail
    # pylint: disable=line-too-long
    with patch_load_json as mock_load_json, patch_file as mock_file, patch_path_is_file as mock_path_is_file, patch_load_file as mock_load_file, patch_get_request as mock_get_request, patch_get_from_url as mock_get_from_url, patch_get_from_s3 as mock_get_from_s3:  # noqa: B950
        schemas = loader.load_type_schemas(schemas_to_load)

        mock_load_json.assert_has_calls(
            calls=[
                call(TEST_TARGET_SCHEMA_JSON),
                call(MULTIPLE_TEST_TARGET_SCHEMAS_JSON),
            ],
            any_order=True,
        )

        mock_path_is_file.assert_any_call(TEST_TARGET_SCHEMA_FILE_PATH)
        mock_load_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH)
        mock_file.assert_called_with(
            TEST_TARGET_SCHEMA_FILE_PATH, "r", encoding="utf-8"
        )

        mock_get_from_url.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI)
        mock_get_request.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI, timeout=60)

        mock_get_from_s3.assert_called_with(
            TEST_TARGET_SCHEMA_BUCKET, TEST_TARGET_SCHEMA_KEY
        )
        loader.s3_client.get_object.assert_called_once_with(
            Bucket=TEST_TARGET_SCHEMA_BUCKET, Key=TEST_TARGET_SCHEMA_KEY
        )

        assert schemas == {
            type_name: get_test_schema(type_name)
            for type_name in [
                "AWS::Test::Target",
                "AWS::Other::Target",
                "MyCompany::Test::Target",
                "Another::Test::Target",
                "MyFile::Hook::Target",
                "MyHttp::Hook::Target",
                "MyS3::Hook::Target",
            ]
        }


def test_load_type_schema_from_json(loader):
    with patch.object(
        loader, "load_type_schema_from_json", wraps=loader.load_type_schema_from_json
    ) as mock_load_json:
        type_schema = loader.load_type_schema(TEST_TARGET_SCHEMA_JSON)

    assert_dict_equals(TEST_TARGET_SCHEMA, type_schema)
    mock_load_json.assert_called_with(TEST_TARGET_SCHEMA_JSON)


def test_load_type_schema_from_invalid_json(loader):
    with patch.object(
        loader, "load_type_schema_from_json", wraps=loader.load_type_schema_from_json
    ) as mock_load_json:
        with pytest.raises(InvalidTypeSchemaError):
            loader.load_type_schema('{"Credentials" :{"ApiKey": "123", xxxx}}')

    mock_load_json.assert_called_with('{"Credentials" :{"ApiKey": "123", xxxx}}')


def test_load_type_schema_from_json_array(loader):
    with patch.object(
        loader, "load_type_schema_from_json", wraps=loader.load_type_schema_from_json
    ) as mock_load_json:
        type_schema = loader.load_type_schema(TEST_TARGET_SCHEMA_JSON_ARRAY)

    assert [TEST_TARGET_SCHEMA] == type_schema
    mock_load_json.assert_called_with(TEST_TARGET_SCHEMA_JSON_ARRAY)


def test_load_type_schema_from_invalid_json_array(loader):
    with patch.object(
        loader, "load_type_schema_from_json", wraps=loader.load_type_schema_from_json
    ) as mock_load_json:
        with pytest.raises(InvalidTypeSchemaError):
            loader.load_type_schema('[{"Credentials" :{"ApiKey": "123"}}]]')

    mock_load_json.assert_called_with('[{"Credentials" :{"ApiKey": "123"}}]]')


def test_load_type_schema_from_file(loader):
    patch_file = patch("builtins.open", mock_open(read_data=TEST_TARGET_SCHEMA_JSON))
    patch_path_is_file = patch(
        "rpdk.core.type_schema_loader.os.path.isfile", return_value=True
    )
    patch_load_file = patch.object(
        loader, "load_type_schema_from_file", wraps=loader.load_type_schema_from_file
    )

    with patch_file as mock_file, patch_path_is_file as mock_path_is_file, patch_load_file as mock_load_file:
        type_schema = loader.load_type_schema(TEST_TARGET_SCHEMA_FILE_PATH)

    assert_dict_equals(TEST_TARGET_SCHEMA, type_schema)
    mock_path_is_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH)
    mock_load_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH)
    mock_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH, "r", encoding="utf-8")


def test_load_type_schema_from_file_file_not_found(loader):
    e = FileNotFoundError("File not found")
    patch_file = patch("builtins.open", mock_open())
    patch_path_is_file = patch(
        "rpdk.core.type_schema_loader.os.path.isfile", return_value=True
    )
    patch_load_file = patch.object(
        loader, "load_type_schema_from_file", wraps=loader.load_type_schema_from_file
    )
    with patch_file as mock_file, patch_path_is_file as mock_path_is_file, patch_load_file as mock_load_file:
        mock_file.side_effect = e
        with pytest.raises(InvalidTypeSchemaError) as excinfo:
            loader.load_type_schema(TEST_TARGET_SCHEMA_FILE_PATH)

    mock_path_is_file.assert_has_calls(calls=[call(TEST_TARGET_SCHEMA_FILE_PATH)])
    mock_load_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH)
    mock_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH, "r", encoding="utf-8")
    assert excinfo.value.__cause__ is e


def test_load_type_schema_from_file_uri(loader):
    patch_file = patch("builtins.open", mock_open(read_data=TEST_TARGET_SCHEMA_JSON))
    patch_load_from_uri = patch.object(
        loader, "load_type_schema_from_uri", wraps=loader.load_type_schema_from_uri
    )
    patch_load_file = patch.object(
        loader, "load_type_schema_from_file", wraps=loader.load_type_schema_from_file
    )

    with patch_file as mock_file, patch_load_from_uri as mock_load_from_uri, patch_load_file as mock_load_file:
        type_schema = loader.load_type_schema(TEST_TARGET_SCHEMA_FILE_URI)

    assert_dict_equals(TEST_TARGET_SCHEMA, type_schema)
    mock_load_from_uri.assert_called_with(TEST_TARGET_SCHEMA_FILE_URI)
    mock_load_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH)
    mock_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH, "r", encoding="utf-8")


def test_load_type_schema_from_file_uri_file_not_found(loader):
    e = FileNotFoundError("File Not Found")
    patch_file = patch("builtins.open", mock_open())
    patch_load_from_uri = patch.object(
        loader, "load_type_schema_from_uri", wraps=loader.load_type_schema_from_uri
    )
    patch_load_file = patch.object(
        loader, "load_type_schema_from_file", wraps=loader.load_type_schema_from_file
    )

    with patch_file as mock_file, patch_load_from_uri as mock_load_from_uri, patch_load_file as mock_load_file:
        mock_file.side_effect = e
        with pytest.raises(InvalidTypeSchemaError) as excinfo:
            loader.load_type_schema(TEST_TARGET_SCHEMA_FILE_URI)

    mock_load_from_uri.assert_called_with(TEST_TARGET_SCHEMA_FILE_URI)
    mock_load_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH)
    mock_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH, "r", encoding="utf-8")
    assert excinfo.value.__cause__ is e


def test_load_type_schema_from_https_url(loader):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = TEST_TARGET_SCHEMA_JSON.encode("utf-8")

    patch_get_request = patch(
        "rpdk.core.type_schema_loader.requests.get", return_value=mock_response
    )
    patch_load_from_uri = patch.object(
        loader, "load_type_schema_from_uri", wraps=loader.load_type_schema_from_uri
    )
    patch_get_from_url = patch.object(
        loader, "_get_type_schema_from_url", wraps=loader._get_type_schema_from_url
    )

    with patch_get_request as mock_get_request, patch_load_from_uri as mock_load_from_uri, patch_get_from_url as mock_get_from_url:
        type_schema = loader.load_type_schema(TEST_HTTPS_TARGET_SCHEMA_URI)

    assert_dict_equals(TEST_TARGET_SCHEMA, type_schema)
    mock_load_from_uri.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI)
    mock_get_from_url.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI)
    mock_get_request.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI, timeout=60)


def test_load_type_schema_from_https_url_unsuccessful(loader):
    e = HTTPError()
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = e
    patch_get_request = patch(
        "rpdk.core.type_schema_loader.requests.get", return_value=mock_response
    )
    patch_load_from_uri = patch.object(
        loader, "load_type_schema_from_uri", wraps=loader.load_type_schema_from_uri
    )
    patch_get_from_url = patch.object(
        loader, "_get_type_schema_from_url", wraps=loader._get_type_schema_from_url
    )

    with patch_get_request as mock_get_request, patch_load_from_uri as mock_load_from_uri, patch_get_from_url as mock_get_from_url:
        with pytest.raises(DownstreamError) as excinfo:
            loader.load_type_schema(TEST_HTTPS_TARGET_SCHEMA_URI)

    mock_load_from_uri.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI)
    mock_get_from_url.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI)
    mock_get_request.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI, timeout=60)
    assert excinfo.value.__cause__ is e


def test_load_type_schema_from_s3(loader):
    loader.s3_client.get_object.return_value = {
        "Body": BytesIO(TEST_TARGET_SCHEMA_JSON.encode("utf-8"))
    }

    patch_load_from_uri = patch.object(
        loader, "load_type_schema_from_uri", wraps=loader.load_type_schema_from_uri
    )
    patch_get_from_s3 = patch.object(
        loader, "_get_type_schema_from_s3", wraps=loader._get_type_schema_from_s3
    )

    with patch_load_from_uri as mock_load_from_uri, patch_get_from_s3 as mock_get_from_s3:
        type_schema = loader.load_type_schema(TEST_S3_TARGET_SCHEMA_URI)

    assert_dict_equals(TEST_TARGET_SCHEMA, type_schema)
    mock_load_from_uri.assert_called_with(TEST_S3_TARGET_SCHEMA_URI)
    mock_get_from_s3.assert_called_with(
        TEST_TARGET_SCHEMA_BUCKET, TEST_TARGET_SCHEMA_KEY
    )
    loader.s3_client.get_object.assert_called_once_with(
        Bucket=TEST_TARGET_SCHEMA_BUCKET, Key=TEST_TARGET_SCHEMA_KEY
    )


def test_load_type_schema_from_s3_client_error(loader):
    e = ClientError(
        {"Error": {"Code": "", "Message": "Bucket does not exist"}},
        "get_object",
    )
    mock_s3_client = loader.s3_client
    mock_s3_client.get_object.side_effect = e

    patch_load_from_uri = patch.object(
        loader, "load_type_schema_from_uri", wraps=loader.load_type_schema_from_uri
    )
    patch_get_from_s3 = patch.object(
        loader, "_get_type_schema_from_s3", wraps=loader._get_type_schema_from_s3
    )

    with patch_load_from_uri as mock_load_from_uri, patch_get_from_s3 as mock_get_from_s3:
        with pytest.raises(DownstreamError) as excinfo:
            loader.load_type_schema(TEST_S3_TARGET_SCHEMA_URI)

    mock_load_from_uri.assert_called_with(TEST_S3_TARGET_SCHEMA_URI)
    mock_get_from_s3.assert_called_with(
        TEST_TARGET_SCHEMA_BUCKET, TEST_TARGET_SCHEMA_KEY
    )
    mock_s3_client.get_object.assert_called_once_with(
        Bucket=TEST_TARGET_SCHEMA_BUCKET, Key=TEST_TARGET_SCHEMA_KEY
    )
    assert excinfo.value.__cause__ is e


def test_load_type_schema_from_cfn_registry(loader):
    mock_cfn = loader.cfn_client
    mock_cfn.describe_type.return_value = {
        "Schema": TEST_TARGET_SCHEMA_JSON,
        "Type": "RESOURCE",
    }

    type_schema = loader.load_schema_from_cfn_registry(
        TEST_TARGET_TYPE_NAME, "RESOURCE"
    )
    assert_dict_equals(TEST_TARGET_SCHEMA, type_schema)
    mock_cfn.describe_type.assert_called_once_with(
        Type="RESOURCE", TypeName=TEST_TARGET_TYPE_NAME
    )


def test_load_type_schema_from_cfn_registry_client_error(loader):
    e = ClientError(
        {"Error": {"Code": "", "Message": "Type does not exist"}},
        "describe_type",
    )
    loader.cfn_client.describe_type.side_effect = e

    with pytest.raises(DownstreamError) as excinfo:
        loader.load_schema_from_cfn_registry(TEST_TARGET_TYPE_NAME, "RESOURCE")

    loader.cfn_client.describe_type.assert_called_once_with(
        Type="RESOURCE", TypeName=TEST_TARGET_TYPE_NAME
    )
    assert excinfo.value.__cause__ is e


def test_load_type_schemas_duplicates(loader):
    duplicate_schema = dict(
        TEST_TARGET_SCHEMA,
        properties={"bar": {"type": "string"}},
        primaryIdentifier=["/properties/bar"],
    )
    schemas_to_load = [TEST_TARGET_SCHEMA_JSON, f"[{json.dumps(duplicate_schema)}]"]

    with pytest.raises(InvalidTypeSchemaError) as excinfo:
        loader.load_type_schemas(schemas_to_load)

    assert f"Duplicate schemas for '{TEST_TARGET_TYPE_NAME}' target type" in str(
        excinfo.value
    )


def test_load_type_schemas_unknown_error(loader):
    patch_load_schema = patch.object(
        loader, "load_type_schema", wraps=loader.load_type_schema, return_value={}
    )

    with patch_load_schema as mock_load_schema, pytest.raises(
        InvalidTypeSchemaError
    ) as excinfo:
        loader.load_type_schemas([TEST_TARGET_SCHEMA_JSON])

    mock_load_schema.assert_called_once_with(TEST_TARGET_SCHEMA_JSON)
    assert "Unknown error while loading type schema" in str(excinfo.value)


def test_load_type_schemas_invalid_schema_format(loader):
    patch_load_schema = patch.object(
        loader, "load_type_schema", wraps=loader.load_type_schema
    )

    with patch_load_schema as mock_load_schema, pytest.raises(
        InvalidTypeSchemaError
    ) as excinfo:
        loader.load_type_schemas(["ftp://unsupportedurlschema.com/test-schema.json"])

    mock_load_schema.assert_called_once_with(
        "ftp://unsupportedurlschema.com/test-schema.json"
    )
    assert (
        "Provided schema is invalid or not supported:"
        " ftp://unsupportedurlschema.com/test-schema.json" in str(excinfo.value)
    )


@pytest.mark.parametrize(
    "uri",
    [
        TEST_TARGET_SCHEMA_FILE_URI,
        TEST_HTTPS_TARGET_SCHEMA_URI,
        TEST_S3_TARGET_SCHEMA_URI,
    ],
)
def test_is_valid_type_schema_uri(uri):
    assert is_valid_type_schema_uri(uri)


@pytest.mark.parametrize(
    "uri", [None, "ftp://unsupportedurlschema.com/test-schema.json"]
)
def test_invalid_type_schema_uri(uri):
    loader = TypeSchemaLoader(Mock(), Mock())
    with pytest.raises(InvalidTypeSchemaError) as excinfo:
        loader.load_type_schema_from_uri(uri)

    assert f"URI provided {uri} is not supported or invalid" in str(excinfo.value)


def test_load_type_schema_from_uri_invalid_local_uri(local_loader):
    with pytest.raises(InvalidTypeSchemaError) as excinfo:
        local_loader.load_type_schema_from_uri(TEST_S3_TARGET_SCHEMA_URI)

    assert f"URI provided is not local: {TEST_S3_TARGET_SCHEMA_URI}" in str(
        excinfo.value
    )


@pytest.mark.parametrize(
    "json_input,expected",
    [
        ("{}", True),
        ("[]", True),
        (b"{}", True),
        (b"[]", True),
        (bytearray("{}", "utf-8"), True),
        (bytearray("[]", "utf-8"), True),
        ({}, False),
        ([], False),
        (21, False),
        (None, False),
    ],
)
def test_is_valid_json(json_input, expected):
    assert TypeSchemaLoader._is_json(json_input) == expected
