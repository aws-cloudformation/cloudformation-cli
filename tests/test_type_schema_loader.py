# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,useless-super-delegation,protected-access
import json
import unittest
from io import BytesIO
from unittest.mock import Mock, mock_open, patch

import pytest
from botocore.exceptions import ClientError

from rpdk.core.type_schema_loader import TypeSchemaLoader, is_valid_type_schema_uri

TEST_TARGET_TYPE_NAME = "AWS::Test::Target"
TEST_TARGET_SCHEMA = {
    "typeName": TEST_TARGET_TYPE_NAME,
    "additionalProperties": False,
    "properties": {},
    "required": [],
}
TEST_TARGET_SCHEMA_JSON = json.dumps(TEST_TARGET_SCHEMA)
TEST_TARGET_SCHEMA_JSON_ARRAY = json.dumps([TEST_TARGET_SCHEMA])
OTHER_TEST_TARGET_FALLBACK_SCHEMA = {
    "typeName": "AWS::Test::Backup",
    "additionalProperties": False,
    "properties": {},
    "required": [],
}
OTHER_TEST_TARGET_FALLBACK_SCHEMA_JSON = json.dumps(OTHER_TEST_TARGET_FALLBACK_SCHEMA)

TEST_TARGET_SCHEMA_BUCKET = "TestTargetSchemaBucket"
TEST_TARGET_SCHEMA_KEY = "test-target-schema.json"
TEST_TARGET_SCHEMA_FILE_PATH = "/files/{}".format(TEST_TARGET_SCHEMA_KEY)
TEST_TARGET_SCHEMA_FILE_URI = "file://{}".format(TEST_TARGET_SCHEMA_FILE_PATH)
TEST_S3_TARGET_SCHEMA_URI = "s3://{}/{}".format(
    TEST_TARGET_SCHEMA_BUCKET, TEST_TARGET_SCHEMA_KEY
)
TEST_HTTPS_TARGET_SCHEMA_URI = "https://{}.s3.us-west-2.amazonaws.com/{}".format(
    TEST_TARGET_SCHEMA_BUCKET, TEST_TARGET_SCHEMA_KEY
)


# pylint: disable=C0103
def assert_dict_equals(d1, d2):
    unittest.TestCase().assertDictEqual(d1, d2)


@pytest.fixture
def loader():
    loader = TypeSchemaLoader(Mock(), Mock())
    return loader


def test_load_type_schema_from_json(loader):
    with patch.object(
        loader, "load_type_schema_from_json", wraps=loader.load_type_schema_from_json
    ) as mock_load_json:
        type_schema = loader.load_type_schema(TEST_TARGET_SCHEMA_JSON)

    assert_dict_equals(TEST_TARGET_SCHEMA, type_schema)
    mock_load_json.assert_called_with(TEST_TARGET_SCHEMA_JSON, None)


def test_load_type_schema_from_invalid_json(loader):
    with patch.object(
        loader, "load_type_schema_from_json", wraps=loader.load_type_schema_from_json
    ) as mock_load_json:
        type_schema = loader.load_type_schema(
            '{"Credentials" :{"ApiKey": "123", xxxx}}'
        )

    assert not type_schema
    mock_load_json.assert_called_with('{"Credentials" :{"ApiKey": "123", xxxx}}', None)


def test_load_type_schema_from_invalid_json_fallback_to_default(loader):
    with patch.object(
        loader, "load_type_schema_from_json", wraps=loader.load_type_schema_from_json
    ) as mock_load_json:
        type_schema = loader.load_type_schema(
            '{"Credentials" :{"ApiKey": "123", xxxx}}',
            OTHER_TEST_TARGET_FALLBACK_SCHEMA,
        )

    assert_dict_equals(OTHER_TEST_TARGET_FALLBACK_SCHEMA, type_schema)
    mock_load_json.assert_called_with(
        '{"Credentials" :{"ApiKey": "123", xxxx}}', OTHER_TEST_TARGET_FALLBACK_SCHEMA
    )


def test_load_type_schema_from_json_array(loader):
    with patch.object(
        loader, "load_type_schema_from_json", wraps=loader.load_type_schema_from_json
    ) as mock_load_json:
        type_schema = loader.load_type_schema(TEST_TARGET_SCHEMA_JSON_ARRAY)

    assert [TEST_TARGET_SCHEMA] == type_schema
    mock_load_json.assert_called_with(TEST_TARGET_SCHEMA_JSON_ARRAY, None)


def test_load_type_schema_from_invalid_json_array(loader):
    with patch.object(
        loader, "load_type_schema_from_json", wraps=loader.load_type_schema_from_json
    ) as mock_load_json:
        type_schema = loader.load_type_schema('[{"Credentials" :{"ApiKey": "123"}}]]')

    assert not type_schema
    mock_load_json.assert_called_with('[{"Credentials" :{"ApiKey": "123"}}]]', None)


def test_load_type_schema_from_invalid_json_array_fallback_to_default(loader):
    with patch.object(
        loader, "load_type_schema_from_json", wraps=loader.load_type_schema_from_json
    ) as mock_load_json:
        type_schema = loader.load_type_schema(
            '[{"Credentials" :{"ApiKey": "123"}}]]',
            OTHER_TEST_TARGET_FALLBACK_SCHEMA,
        )

    assert_dict_equals(OTHER_TEST_TARGET_FALLBACK_SCHEMA, type_schema)
    mock_load_json.assert_called_with(
        '[{"Credentials" :{"ApiKey": "123"}}]]', OTHER_TEST_TARGET_FALLBACK_SCHEMA
    )


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
    mock_load_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH, None)
    mock_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH, "r")


def test_load_type_schema_from_file_file_not_found(loader):
    patch_file = patch("builtins.open", mock_open())
    patch_path_is_file = patch(
        "rpdk.core.type_schema_loader.os.path.isfile", return_value=True
    )
    patch_load_file = patch.object(
        loader, "load_type_schema_from_file", wraps=loader.load_type_schema_from_file
    )

    with patch_file as mock_file, patch_path_is_file as mock_path_is_file, patch_load_file as mock_load_file:
        mock_file.side_effect = FileNotFoundError()
        type_schema = loader.load_type_schema(TEST_TARGET_SCHEMA_FILE_PATH)

    assert not type_schema
    mock_path_is_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH)
    mock_load_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH, None)
    mock_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH, "r")


def test_load_type_schema_from_file_error_fallback_to_default(loader):
    patch_file = patch("builtins.open", mock_open())
    patch_path_is_file = patch(
        "rpdk.core.type_schema_loader.os.path.isfile", return_value=True
    )
    patch_load_file = patch.object(
        loader, "load_type_schema_from_file", wraps=loader.load_type_schema_from_file
    )

    with patch_file as mock_file, patch_path_is_file as mock_path_is_file, patch_load_file as mock_load_file:
        mock_file.side_effect = FileNotFoundError()
        type_schema = loader.load_type_schema(
            TEST_TARGET_SCHEMA_FILE_PATH, OTHER_TEST_TARGET_FALLBACK_SCHEMA
        )

    assert_dict_equals(OTHER_TEST_TARGET_FALLBACK_SCHEMA, type_schema)
    mock_path_is_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH)
    mock_load_file.assert_called_with(
        TEST_TARGET_SCHEMA_FILE_PATH, OTHER_TEST_TARGET_FALLBACK_SCHEMA
    )
    mock_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH, "r")


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
    mock_load_from_uri.assert_called_with(TEST_TARGET_SCHEMA_FILE_URI, None)
    mock_load_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH, None)
    mock_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH, "r")


def test_load_type_schema_from_file_uri_file_not_found(loader):
    patch_file = patch("builtins.open", mock_open())
    patch_load_from_uri = patch.object(
        loader, "load_type_schema_from_uri", wraps=loader.load_type_schema_from_uri
    )
    patch_load_file = patch.object(
        loader, "load_type_schema_from_file", wraps=loader.load_type_schema_from_file
    )

    with patch_file as mock_file, patch_load_from_uri as mock_load_from_uri, patch_load_file as mock_load_file:
        mock_file.side_effect = FileNotFoundError()
        type_schema = loader.load_type_schema(TEST_TARGET_SCHEMA_FILE_URI)

    assert not type_schema
    mock_load_from_uri.assert_called_with(TEST_TARGET_SCHEMA_FILE_URI, None)
    mock_load_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH, None)
    mock_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH, "r")


def test_load_type_schema_from_file_uri_error_fallback_to_default(loader):
    patch_file = patch("builtins.open", mock_open())
    patch_load_from_uri = patch.object(
        loader, "load_type_schema_from_uri", wraps=loader.load_type_schema_from_uri
    )
    patch_load_file = patch.object(
        loader, "load_type_schema_from_file", wraps=loader.load_type_schema_from_file
    )

    with patch_file as mock_file, patch_load_from_uri as mock_load_from_uri, patch_load_file as mock_load_file:
        mock_file.side_effect = FileNotFoundError()
        type_schema = loader.load_type_schema(
            TEST_TARGET_SCHEMA_FILE_URI, OTHER_TEST_TARGET_FALLBACK_SCHEMA
        )

    assert_dict_equals(OTHER_TEST_TARGET_FALLBACK_SCHEMA, type_schema)
    mock_load_from_uri.assert_called_with(
        TEST_TARGET_SCHEMA_FILE_URI, OTHER_TEST_TARGET_FALLBACK_SCHEMA
    )
    mock_load_file.assert_called_with(
        TEST_TARGET_SCHEMA_FILE_PATH, OTHER_TEST_TARGET_FALLBACK_SCHEMA
    )
    mock_file.assert_called_with(TEST_TARGET_SCHEMA_FILE_PATH, "r")


def test_load_type_schema_from_https_url(loader):
    mock_request = Mock()
    mock_request.status_code = 200
    mock_request.content = TEST_TARGET_SCHEMA_JSON.encode("utf-8")

    patch_get_request = patch(
        "rpdk.core.type_schema_loader.requests.get", return_value=mock_request
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
    mock_load_from_uri.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI, None)
    mock_get_from_url.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI, None)
    mock_get_request.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI, timeout=60)


def test_load_type_schema_from_https_url_unsuccessful(loader):
    mock_request = Mock()
    mock_request.status_code = 404

    patch_get_request = patch(
        "rpdk.core.type_schema_loader.requests.get", return_value=mock_request
    )
    patch_load_from_uri = patch.object(
        loader, "load_type_schema_from_uri", wraps=loader.load_type_schema_from_uri
    )
    patch_get_from_url = patch.object(
        loader, "_get_type_schema_from_url", wraps=loader._get_type_schema_from_url
    )

    with patch_get_request as mock_get_request, patch_load_from_uri as mock_load_from_uri, patch_get_from_url as mock_get_from_url:
        type_schema = loader.load_type_schema(TEST_HTTPS_TARGET_SCHEMA_URI)

    assert not type_schema
    mock_load_from_uri.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI, None)
    mock_get_from_url.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI, None)
    mock_get_request.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI, timeout=60)


def test_load_type_schema_from_https_url_unsuccessful_fallback_to_default(loader):
    mock_request = Mock()
    mock_request.status_code = 404

    patch_get_request = patch(
        "rpdk.core.type_schema_loader.requests.get", return_value=mock_request
    )
    patch_load_from_uri = patch.object(
        loader, "load_type_schema_from_uri", wraps=loader.load_type_schema_from_uri
    )
    patch_get_from_url = patch.object(
        loader, "_get_type_schema_from_url", wraps=loader._get_type_schema_from_url
    )

    with patch_get_request as mock_get_request, patch_load_from_uri as mock_load_from_uri, patch_get_from_url as mock_get_from_url:
        type_schema = loader.load_type_schema(
            TEST_HTTPS_TARGET_SCHEMA_URI, OTHER_TEST_TARGET_FALLBACK_SCHEMA
        )

    assert_dict_equals(OTHER_TEST_TARGET_FALLBACK_SCHEMA, type_schema)
    mock_load_from_uri.assert_called_with(
        TEST_HTTPS_TARGET_SCHEMA_URI, OTHER_TEST_TARGET_FALLBACK_SCHEMA
    )
    mock_get_from_url.assert_called_with(
        TEST_HTTPS_TARGET_SCHEMA_URI, OTHER_TEST_TARGET_FALLBACK_SCHEMA
    )
    mock_get_request.assert_called_with(TEST_HTTPS_TARGET_SCHEMA_URI, timeout=60)


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
    mock_load_from_uri.assert_called_with(TEST_S3_TARGET_SCHEMA_URI, None)
    mock_get_from_s3.assert_called_with(
        TEST_TARGET_SCHEMA_BUCKET, TEST_TARGET_SCHEMA_KEY, None
    )
    loader.s3_client.get_object.assert_called_once_with(
        Bucket=TEST_TARGET_SCHEMA_BUCKET, Key=TEST_TARGET_SCHEMA_KEY
    )


def test_load_type_schema_from_s3_client_error(loader):
    loader.s3_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "", "Message": "Bucket does not exist"}},
        "get_object",
    )

    patch_load_from_uri = patch.object(
        loader, "load_type_schema_from_uri", wraps=loader.load_type_schema_from_uri
    )
    patch_get_from_s3 = patch.object(
        loader, "_get_type_schema_from_s3", wraps=loader._get_type_schema_from_s3
    )

    with patch_load_from_uri as mock_load_from_uri, patch_get_from_s3 as mock_get_from_s3:
        type_schema = loader.load_type_schema(TEST_S3_TARGET_SCHEMA_URI)

    assert not type_schema
    mock_load_from_uri.assert_called_with(TEST_S3_TARGET_SCHEMA_URI, None)
    mock_get_from_s3.assert_called_with(
        TEST_TARGET_SCHEMA_BUCKET, TEST_TARGET_SCHEMA_KEY, None
    )
    loader.s3_client.get_object.assert_called_once_with(
        Bucket=TEST_TARGET_SCHEMA_BUCKET, Key=TEST_TARGET_SCHEMA_KEY
    )


def test_load_type_schema_from_s3_error_fallback_to_default(loader):
    loader.s3_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "", "Message": "Bucket does not exist"}},
        "get_object",
    )

    patch_load_from_uri = patch.object(
        loader, "load_type_schema_from_uri", wraps=loader.load_type_schema_from_uri
    )
    patch_get_from_s3 = patch.object(
        loader, "_get_type_schema_from_s3", wraps=loader._get_type_schema_from_s3
    )

    with patch_load_from_uri as mock_load_from_uri, patch_get_from_s3 as mock_get_from_s3:
        type_schema = loader.load_type_schema(
            TEST_S3_TARGET_SCHEMA_URI, OTHER_TEST_TARGET_FALLBACK_SCHEMA
        )

    assert_dict_equals(OTHER_TEST_TARGET_FALLBACK_SCHEMA, type_schema)
    mock_load_from_uri.assert_called_with(
        TEST_S3_TARGET_SCHEMA_URI, OTHER_TEST_TARGET_FALLBACK_SCHEMA
    )
    mock_get_from_s3.assert_called_with(
        TEST_TARGET_SCHEMA_BUCKET,
        TEST_TARGET_SCHEMA_KEY,
        OTHER_TEST_TARGET_FALLBACK_SCHEMA,
    )
    loader.s3_client.get_object.assert_called_once_with(
        Bucket=TEST_TARGET_SCHEMA_BUCKET, Key=TEST_TARGET_SCHEMA_KEY
    )


def test_load_type_schema_from_cfn_registry(loader):
    loader.cfn_client.describe_type.return_value = {
        "Schema": TEST_TARGET_SCHEMA_JSON,
        "Type": "RESOURCE",
        "ProvisioningType": "FULLY_MUTABLE",
    }

    type_schema, target_type, provisioning_type = loader.load_schema_from_cfn_registry(
        TEST_TARGET_TYPE_NAME, "RESOURCE"
    )

    assert_dict_equals(TEST_TARGET_SCHEMA, type_schema)
    assert target_type == "RESOURCE"
    assert provisioning_type == "FULLY_MUTABLE"
    loader.cfn_client.describe_type.assert_called_once_with(
        Type="RESOURCE", TypeName=TEST_TARGET_TYPE_NAME
    )


def test_load_type_schema_from_cfn_registry_client_error(loader):
    loader.cfn_client.describe_type.side_effect = ClientError(
        {"Error": {"Code": "", "Message": "Type does not exist"}},
        "get_object",
    )

    type_schema, target_type, provisioning_type = loader.load_schema_from_cfn_registry(
        TEST_TARGET_TYPE_NAME, "RESOURCE"
    )

    assert not type_schema
    assert not target_type
    assert not provisioning_type
    loader.cfn_client.describe_type.assert_called_once_with(
        Type="RESOURCE", TypeName=TEST_TARGET_TYPE_NAME
    )


def test_load_type_schema_from_cfn_registry_error_fallback_to_default(loader):
    loader.cfn_client.describe_type.side_effect = ClientError(
        {"Error": {"Code": "", "Message": "Type does not exist"}},
        "get_object",
    )

    type_schema, target_type, provisioning_type = loader.load_schema_from_cfn_registry(
        TEST_TARGET_TYPE_NAME, "RESOURCE", OTHER_TEST_TARGET_FALLBACK_SCHEMA
    )

    assert_dict_equals(OTHER_TEST_TARGET_FALLBACK_SCHEMA, type_schema)
    assert not target_type
    assert not provisioning_type
    loader.cfn_client.describe_type.assert_called_once_with(
        Type="RESOURCE", TypeName=TEST_TARGET_TYPE_NAME
    )


def test_get_provision_type(loader):
    loader.cfn_client.describe_type.return_value = {
        "Schema": TEST_TARGET_SCHEMA_JSON,
        "Type": "RESOURCE",
        "ProvisioningType": "IMMUTABLE",
    }

    provisioning_type = loader.get_provision_type(TEST_TARGET_TYPE_NAME, "RESOURCE")

    assert provisioning_type == "IMMUTABLE"
    loader.cfn_client.describe_type.assert_called_once_with(
        Type="RESOURCE", TypeName=TEST_TARGET_TYPE_NAME
    )


def test_get_provision_type_client_error(loader):
    loader.cfn_client.describe_type.side_effect = ClientError(
        {"Error": {"Code": "", "Message": "Type does not exist"}},
        "get_object",
    )

    provisioning_type = loader.get_provision_type(TEST_TARGET_TYPE_NAME, "RESOURCE")

    assert not provisioning_type
    loader.cfn_client.describe_type.assert_called_once_with(
        Type="RESOURCE", TypeName=TEST_TARGET_TYPE_NAME
    )


def test_load_type_schema_null_input(loader):
    type_schema = loader.load_type_schema(None, OTHER_TEST_TARGET_FALLBACK_SCHEMA)
    assert_dict_equals(OTHER_TEST_TARGET_FALLBACK_SCHEMA, type_schema)

    type_schema = loader.load_type_schema_from_json(
        None, OTHER_TEST_TARGET_FALLBACK_SCHEMA
    )
    assert_dict_equals(OTHER_TEST_TARGET_FALLBACK_SCHEMA, type_schema)

    type_schema = loader.load_type_schema_from_uri(
        None, OTHER_TEST_TARGET_FALLBACK_SCHEMA
    )
    assert_dict_equals(OTHER_TEST_TARGET_FALLBACK_SCHEMA, type_schema)

    type_schema = loader.load_type_schema_from_file(
        None, OTHER_TEST_TARGET_FALLBACK_SCHEMA
    )
    assert_dict_equals(OTHER_TEST_TARGET_FALLBACK_SCHEMA, type_schema)


def test_load_type_schema_invalid_input(loader):
    type_schema = loader.load_type_schema(
        "This is invalid input", OTHER_TEST_TARGET_FALLBACK_SCHEMA
    )
    assert_dict_equals(OTHER_TEST_TARGET_FALLBACK_SCHEMA, type_schema)

    with patch(
        "rpdk.core.type_schema_loader.is_valid_type_schema_uri", return_value=True
    ):
        type_schema = loader.load_type_schema_from_uri(
            "ftp://unsupportedurlschema.com/test-schema.json",
            OTHER_TEST_TARGET_FALLBACK_SCHEMA,
        )
    assert_dict_equals(OTHER_TEST_TARGET_FALLBACK_SCHEMA, type_schema)


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
def test_is_invalid_type_schema_uri(uri):
    assert not is_valid_type_schema_uri(uri)
