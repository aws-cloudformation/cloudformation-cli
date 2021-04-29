# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,protected-access
import logging
import time
from io import StringIO
from unittest.mock import ANY, patch

import pytest

from rpdk.core.boto_helpers import LOWER_CAMEL_CRED_KEYS
from rpdk.core.contract.interface import Action, HandlerErrorCode, OperationStatus
from rpdk.core.contract.resource_client import (
    ResourceClient,
    override_properties,
    prune_properties,
    prune_properties_from_model,
    prune_properties_if_not_exist_in_path,
    prune_properties_which_dont_exist_in_path,
)
from rpdk.core.exceptions import InvalidProjectError
from rpdk.core.test import (
    DEFAULT_ENDPOINT,
    DEFAULT_FUNCTION,
    DEFAULT_REGION,
    empty_override,
)

EMPTY_OVERRIDE = empty_override()
ACCOUNT = "11111111"
LOG = logging.getLogger(__name__)

SCHEMA = {
    "properties": {
        "a": {"type": "number", "const": 1},
        "b": {"type": "number", "const": 2},
        "c": {"type": "number", "const": 3},
        "d": {"type": "number", "const": 4},
    },
    "readOnlyProperties": ["/properties/b"],
    "createOnlyProperties": ["/properties/c"],
    "primaryIdentifier": ["/properties/c"],
    "writeOnlyProperties": ["/properties/d"],
}

SCHEMA_WITH_MULTIPLE_WRITE_PROPERTIES = {
    "properties": {
        "a": {"type": "number", "const": 1},
        "b": {"type": "number", "const": 2},
        "c": {"type": "number", "const": 3},
        "d": {"type": "number", "const": 4},
    },
    "readOnlyProperties": ["/properties/b"],
    "createOnlyProperties": ["/properties/c"],
    "primaryIdentifier": ["/properties/c"],
    "writeOnlyProperties": ["/properties/d", "/properties/a"],
}

SCHEMA_ = {
    "properties": {
        "a": {"type": "number"},
        "b": {"type": "number"},
        "c": {"type": "number"},
        "d": {"type": "number"},
    },
    "readOnlyProperties": ["/properties/b"],
    "createOnlyProperties": ["/properties/c"],
    "primaryIdentifier": ["/properties/c"],
    "writeOnlyProperties": ["/properties/d"],
}

SCHEMA_WITH_NESTED_PROPERTIES = {
    "properties": {
        "a": {"type": "string"},
        "g": {"type": "number"},
        "b": {"$ref": "#/definitions/c"},
        "f": {
            "type": "array",
            "items": {"$ref": "#/definitions/c"},
        },
        "h": {
            "type": "array",
            "insertionOrder": "false",
            "items": {"$ref": "#/definitions/c"},
        },
    },
    "definitions": {
        "c": {
            "type": "object",
            "properties": {"d": {"type": "integer"}, "e": {"type": "integer"}},
        }
    },
    "readOnlyProperties": ["/properties/a"],
    "primaryIdentifier": ["/properties/a"],
    "writeOnlyProperties": ["/properties/g"],
}

SCHEMA_WITH_COMPOSITE_KEY = {
    "properties": {
        "a": {"type": "number"},
        "b": {"type": "number"},
        "c": {"type": "number"},
        "d": {"type": "number"},
    },
    "readOnlyProperties": ["/properties/d"],
    "createOnlyProperties": ["/properties/c"],
    "primaryIdentifier": ["/properties/c", "/properties/d"],
}

SCHEMA_WITH_ADDITIONAL_IDENTIFIERS = {
    "properties": {
        "a": {"type": "number"},
        "b": {"type": "number"},
        "c": {"type": "number"},
        "d": {"type": "number"},
    },
    "readOnlyProperties": ["/properties/b"],
    "createOnlyProperties": ["/properties/c"],
    "primaryIdentifier": ["/properties/c"],
    "additionalIdentifiers": [["/properties/b"]],
}


@pytest.fixture
def resource_client():
    endpoint = "https://"
    patch_sesh = patch(
        "rpdk.core.contract.resource_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_account = patch(
        "rpdk.core.contract.resource_client.get_account",
        autospec=True,
        return_value=ACCOUNT,
    )
    with patch_sesh as mock_create_sesh, patch_creds as mock_creds:
        with patch_account as mock_account:
            mock_sesh = mock_create_sesh.return_value
            mock_sesh.region_name = DEFAULT_REGION
            client = ResourceClient(
                DEFAULT_FUNCTION, endpoint, DEFAULT_REGION, {}, EMPTY_OVERRIDE
            )

    mock_sesh.client.assert_called_once_with("lambda", endpoint_url=endpoint)
    mock_creds.assert_called_once_with(mock_sesh, LOWER_CAMEL_CRED_KEYS, None)
    mock_account.assert_called_once_with(mock_sesh, {})
    assert client._function_name == DEFAULT_FUNCTION
    assert client._schema == {}
    assert client._overrides == EMPTY_OVERRIDE
    assert client.account == ACCOUNT

    return client


@pytest.fixture
def resource_client_inputs():
    endpoint = "https://"
    patch_sesh = patch(
        "rpdk.core.contract.resource_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_account = patch(
        "rpdk.core.contract.resource_client.get_account",
        autospec=True,
        return_value=ACCOUNT,
    )
    with patch_sesh as mock_create_sesh, patch_creds as mock_creds:
        with patch_account as mock_account:
            mock_sesh = mock_create_sesh.return_value
            mock_sesh.region_name = DEFAULT_REGION
            client = ResourceClient(
                DEFAULT_FUNCTION,
                endpoint,
                DEFAULT_REGION,
                {},
                EMPTY_OVERRIDE,
                {"CREATE": {"a": 1}, "UPDATE": {"a": 2}, "INVALID": {"b": 2}},
            )

    mock_sesh.client.assert_called_once_with("lambda", endpoint_url=endpoint)
    mock_creds.assert_called_once_with(mock_sesh, LOWER_CAMEL_CRED_KEYS, None)
    mock_account.assert_called_once_with(mock_sesh, {})

    assert client._function_name == DEFAULT_FUNCTION
    assert client._schema == {}
    assert client._overrides == EMPTY_OVERRIDE
    assert client.account == ACCOUNT

    return client


@pytest.fixture(params=[SCHEMA_, SCHEMA_WITH_ADDITIONAL_IDENTIFIERS])
def resource_client_inputs_schema(request):
    endpoint = "https://"
    patch_sesh = patch(
        "rpdk.core.contract.resource_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_account = patch(
        "rpdk.core.contract.resource_client.get_account",
        autospec=True,
        return_value=ACCOUNT,
    )
    with patch_sesh as mock_create_sesh, patch_creds as mock_creds:
        with patch_account as mock_account:
            mock_sesh = mock_create_sesh.return_value
            mock_sesh.region_name = DEFAULT_REGION
            client = ResourceClient(
                DEFAULT_FUNCTION,
                endpoint,
                DEFAULT_REGION,
                request.param,
                EMPTY_OVERRIDE,
                {
                    "CREATE": {"a": 111, "c": 2, "d": 3},
                    "UPDATE": {"a": 1, "c": 2},
                    "INVALID": {"c": 3},
                },
            )

    mock_sesh.client.assert_called_once_with("lambda", endpoint_url=endpoint)
    mock_creds.assert_called_once_with(mock_sesh, LOWER_CAMEL_CRED_KEYS, None)
    mock_account.assert_called_once_with(mock_sesh, {})

    assert client._function_name == DEFAULT_FUNCTION
    assert client._schema == request.param
    assert client._overrides == EMPTY_OVERRIDE
    assert client.account == ACCOUNT

    return client


@pytest.fixture
def resource_client_inputs_composite_key():
    endpoint = "https://"
    patch_sesh = patch(
        "rpdk.core.contract.resource_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_account = patch(
        "rpdk.core.contract.resource_client.get_account",
        autospec=True,
        return_value=ACCOUNT,
    )
    with patch_sesh as mock_create_sesh, patch_creds as mock_creds:
        with patch_account as mock_account:
            mock_sesh = mock_create_sesh.return_value
            mock_sesh.region_name = DEFAULT_REGION
            client = ResourceClient(
                DEFAULT_FUNCTION,
                endpoint,
                DEFAULT_REGION,
                SCHEMA_WITH_COMPOSITE_KEY,
                EMPTY_OVERRIDE,
                {
                    "CREATE": {"a": 111, "c": 2},
                    "UPDATE": {"a": 1, "c": 2},
                    "INVALID": {"c": 3},
                },
            )

    mock_sesh.client.assert_called_once_with("lambda", endpoint_url=endpoint)
    mock_creds.assert_called_once_with(mock_sesh, LOWER_CAMEL_CRED_KEYS, None)
    mock_account.assert_called_once_with(mock_sesh, {})

    assert client._function_name == DEFAULT_FUNCTION
    assert client._schema == SCHEMA_WITH_COMPOSITE_KEY
    assert client._overrides == EMPTY_OVERRIDE
    assert client.account == ACCOUNT

    return client


def test_prune_properties():
    document = {
        "foo": "bar",
        "spam": "eggs",
        "one": "two",
        "array": ["first", "second"],
    }
    prune_properties(document, [("foo",), ("spam",), ("not_found",), ("array", "1")])
    assert document == {"one": "two", "array": ["first"]}


def test_prune_properties_from_model():
    document = {
        "foo": "bar",
        "spam": "eggs",
        "one": "two",
        "array": ["first", "second"],
    }
    prune_properties_from_model(
        document,
        [
            ("properties", "foo"),
            ("properties", "spam"),
            ("properties", "not_found"),
            ("properties", "array", "1"),
        ],
    )
    assert document == {"one": "two", "array": ["first"]}


def test_prune_properties_if_not_exist_in_path():
    previous_model = {
        "spam": "eggs",
        "one": "two",
        "array": ["first", "second"],
    }
    model = {
        "foo": "bar",
        "spam": "eggs",
        "one": "two",
        "array": ["first", "second"],
    }
    model = prune_properties_if_not_exist_in_path(
        model,
        previous_model,
        [
            ("properties", "foo"),
            ("properties", "spam"),
            ("properties", "array", "1"),
            ("properties", "invalid"),
        ],
    )
    assert model == previous_model


def test_prune_properties_which_dont_exist_in_path():
    model = {
        "spam": "eggs",
        "one": "two",
        "array": ["first", "second"],
    }
    model1 = prune_properties_which_dont_exist_in_path(
        model,
        [
            ("properties", "one"),
        ],
    )
    assert model1 == {"one": "two"}


def test_init_sam_cli_client():
    patch_sesh = patch(
        "rpdk.core.contract.resource_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_account = patch(
        "rpdk.core.contract.resource_client.get_account",
        autospec=True,
        return_value=ACCOUNT,
    )
    with patch_sesh as mock_create_sesh, patch_creds as mock_creds:
        with patch_account as mock_account:
            mock_sesh = mock_create_sesh.return_value
            mock_sesh.region_name = DEFAULT_REGION
            client = ResourceClient(
                DEFAULT_FUNCTION, DEFAULT_ENDPOINT, DEFAULT_REGION, {}, EMPTY_OVERRIDE
            )

    mock_sesh.client.assert_called_once_with(
        "lambda", endpoint_url=DEFAULT_ENDPOINT, use_ssl=False, verify=False, config=ANY
    )
    mock_creds.assert_called_once_with(mock_sesh, LOWER_CAMEL_CRED_KEYS, None)
    mock_account.assert_called_once_with(mock_sesh, {})
    assert client.account == ACCOUNT


def test_generate_token():
    token = ResourceClient.generate_token()
    assert isinstance(token, str)
    assert len(token) == 36


def test_make_request():
    desired_resource_state = object()
    previous_resource_state = object()
    token = object()
    request = ResourceClient.make_request(
        desired_resource_state,
        previous_resource_state,
        "us-east-1",
        ACCOUNT,
        "CREATE",
        {},
        token,
    )
    assert request == {
        "requestData": {
            "callerCredentials": {},
            "resourceProperties": desired_resource_state,
            "previousResourceProperties": previous_resource_state,
            "logicalResourceId": token,
        },
        "region": DEFAULT_REGION,
        "awsAccountId": ACCOUNT,
        "action": "CREATE",
        "bearerToken": token,
        "callbackContext": None,
    }


def test_get_metadata(resource_client):
    schema = {
        "properties": {
            "a": {"type": "array", "const": 1, "insertionOrder": "true"},
            "b": {"type": "number", "const": 2, "insertionOrder": "false"},
            "c": {"type": "number", "const": 3},
            "d": {"type": "number", "const": 4},
        },
        "readOnlyProperties": ["/properties/c"],
        "createOnlyProperties": ["/properties/d"],
    }
    resource_client._update_schema(schema)
    assert resource_client.get_metadata() == {"b"}


def test_update_schema(resource_client):
    resource_client._strategy = object()

    schema = {
        "primaryIdentifier": ["/properties/a"],
        "readOnlyProperties": ["/properties/b"],
        "writeOnlyProperties": ["/properties/c"],
        "createOnlyProperties": ["/properties/d"],
    }
    resource_client._update_schema(schema)

    assert resource_client._schema is schema
    assert resource_client._strategy is None
    assert resource_client.primary_identifier_paths == {("properties", "a")}
    assert resource_client.read_only_paths == {("properties", "b")}
    assert resource_client.write_only_paths == {("properties", "c")}
    assert resource_client.create_only_paths == {("properties", "d")}


def test_strategy(resource_client):
    schema = {
        "properties": {
            "a": {"type": "number", "const": 1},
            "b": {"type": "number", "const": 2},
            "c": {"type": "number", "const": 3},
            "d": {"type": "number", "const": 4},
        },
        "readOnlyProperties": ["/properties/c"],
        "createOnlyProperties": ["/properties/d"],
    }
    resource_client._update_schema(schema)

    assert resource_client._schema is schema
    assert resource_client._strategy is None

    strategy = resource_client.strategy

    assert resource_client._strategy is strategy
    assert strategy.example() == {"a": 1, "b": 2, "d": 4}

    cached = resource_client.strategy

    assert cached is strategy
    assert resource_client._strategy is strategy


def test_invalid_strategy(resource_client):
    schema = {
        "properties": {
            "a": {"type": "number", "const": 1},
            "b": {"type": "number", "const": 2},
            "c": {"type": "number", "const": 3},
            "d": {"type": "number", "const": 4},
        },
        "readOnlyProperties": ["/properties/c"],
        "createOnlyProperties": ["/properties/d"],
    }
    resource_client._update_schema(schema)

    assert resource_client._schema is schema
    assert resource_client._strategy is None

    invalid_strategy = resource_client.invalid_strategy

    assert resource_client._invalid_strategy is invalid_strategy
    assert invalid_strategy.example() == {"a": 1, "b": 2, "c": 3, "d": 4}

    cached = resource_client.invalid_strategy

    assert cached is invalid_strategy
    assert resource_client._invalid_strategy is invalid_strategy


def test_update_strategy(resource_client):
    schema = {
        "properties": {
            "a": {"type": "number", "const": 1},
            "b": {"type": "number", "const": 2},
            "c": {"type": "number", "const": 3},
            "d": {"type": "number", "const": 4},
        },
        "readOnlyProperties": ["/properties/c"],
        "createOnlyProperties": ["/properties/d"],
    }
    resource_client._update_schema(schema)

    assert resource_client._schema is schema
    assert resource_client._update_strategy is None

    update_strategy = resource_client.update_strategy

    assert resource_client._update_strategy is update_strategy
    assert update_strategy.example() == {"a": 1, "b": 2}

    cached = resource_client.update_strategy

    assert cached is update_strategy
    assert resource_client._update_strategy is update_strategy


def test_generate_create_example(resource_client):
    schema = {
        "properties": {
            "a": {"type": "number", "const": 1},
            "b": {"type": "number", "const": 2},
        },
        "readOnlyProperties": ["/properties/b"],
    }
    resource_client._update_schema(schema)
    example = resource_client.generate_create_example()
    assert example == {"a": 1}


def test_generate_invalid_create_example(resource_client):
    schema = {
        "properties": {
            "a": {"type": "number", "const": 1},
            "b": {"type": "number", "const": 2},
        },
        "readOnlyProperties": ["/properties/b"],
    }
    resource_client._update_schema(schema)
    example = resource_client.generate_invalid_create_example()
    assert example == {"a": 1, "b": 2}


def test_generate_update_example(resource_client):
    schema = {
        "properties": {
            "a": {"type": "number", "const": 1},
            "b": {"type": "number", "const": 2},
            "c": {"type": "number", "const": 3},
        },
        "readOnlyProperties": ["/properties/b"],
        "createOnlyProperties": ["/properties/c"],
    }
    resource_client._update_schema(schema)
    resource_client._overrides = {}
    model_from_created_resource = {"b": 2, "a": 4}
    example = resource_client.generate_update_example(model_from_created_resource)
    assert example == {"a": 1, "b": 2}


def test_generate_invalid_update_example(resource_client):
    schema = {
        "properties": {
            "a": {"type": "number", "const": 1},
            "b": {"type": "number", "const": 2},
            "c": {"type": "number", "const": 3},
        },
        "readOnlyProperties": ["/properties/b"],
        "createOnlyProperties": ["/properties/c"],
    }
    resource_client._update_schema(schema)
    resource_client._overrides = {}
    model_from_created_resource = {"b": 2, "a": 4}
    example = resource_client.generate_invalid_update_example(
        model_from_created_resource
    )
    assert example == {"a": 1, "b": 2, "c": 3}


def test_generate_update_example_update_override(resource_client):
    schema = {
        "properties": {
            "a": {"type": "number", "const": 1},
            "b": {"type": "number", "const": 2},
            "c": {"type": "number", "const": 3},
        },
        "readOnlyProperties": ["/properties/b"],
        "createOnlyProperties": ["/properties/c"],
    }
    resource_client._update_schema(schema)
    overrides = {"UPDATE": {"a": 2}, "CREATE": {"a": 5}}
    resource_client._overrides = overrides
    model_from_created_resource = {"b": 2, "a": 4}
    example = resource_client.generate_update_example(model_from_created_resource)
    assert example == {"a": 2, "b": 2}


def test_generate_update_example_create_override(resource_client):
    schema = {
        "properties": {
            "a": {"type": "number", "const": 1},
            "b": {"type": "number", "const": 2},
            "c": {"type": "number", "const": 3},
        },
        "readOnlyProperties": ["/properties/b"],
        "createOnlyProperties": ["/properties/c"],
    }
    resource_client._update_schema(schema)
    overrides = {"CREATE": {"a": 5}}
    resource_client._overrides = overrides
    model_from_created_resource = {"b": 2, "a": 4}
    example = resource_client.generate_update_example(model_from_created_resource)
    assert example == {"a": 5, "b": 2}


def test_has_only_writable_identifiers_primary_is_read_only(resource_client):
    resource_client._update_schema(
        {
            "primaryIdentifier": ["/properties/foo"],
            "readOnlyProperties": ["/properties/foo"],
        }
    )

    assert not resource_client.has_only_writable_identifiers()


def test_has_only_writable_identifiers_primary_is_writable(resource_client):
    resource_client._update_schema(
        {
            "primaryIdentifier": ["/properties/foo"],
            "createOnlyProperties": ["/properties/foo"],
        }
    )

    assert resource_client.has_only_writable_identifiers()


def test_has_only_writable_identifiers_primary_and_additional_are_read_only(
    resource_client,
):
    resource_client._update_schema(
        {
            "primaryIdentifier": ["/properties/foo"],
            "additionalIdentifiers": [["/properties/bar"]],
            "readOnlyProperties": ["/properties/foo", "/properties/bar"],
        }
    )

    assert not resource_client.has_only_writable_identifiers()


def test_has_only_writable_identifiers_additional_is_writable(resource_client):
    resource_client._update_schema(
        {
            "primaryIdentifier": ["/properties/foo"],
            "additionalIdentifiers": [["/properties/bar"]],
            "readOnlyProperties": ["/properties/foo"],
        }
    )

    assert not resource_client.has_only_writable_identifiers()


def test_has_only_writable_identifiers_compound_is_writable(resource_client):
    resource_client._update_schema(
        {
            "primaryIdentifier": ["/properties/foo"],
            "additionalIdentifiers": [["/properties/bar", "/properties/baz"]],
            "readOnlyProperties": ["/properties/foo", "/properties/baz"],
        }
    )

    assert not resource_client.has_only_writable_identifiers()


def test_has_only_writable_identifiers_composite_primary_are_read_only(
    resource_client,
):
    resource_client._update_schema(
        {
            "primaryIdentifier": ["/properties/foo", "/properties/bar"],
            "readOnlyProperties": ["/properties/foo", "/properties/bar"],
        }
    )

    assert not resource_client.has_only_writable_identifiers()


def test_has_only_writable_identifiers_composite_primary_is_read_only(
    resource_client,
):
    resource_client._update_schema(
        {
            "primaryIdentifier": ["/properties/foo", "/properties/bar"],
            "readOnlyProperties": ["/properties/foo"],
            "createOnlyProperties": ["/properties/bar"],
        }
    )

    assert not resource_client.has_only_writable_identifiers()


def test_has_only_writable_identifiers_composite_primary_are_writable(
    resource_client,
):
    resource_client._update_schema(
        {
            "primaryIdentifier": ["/properties/foo", "/properties/bar"],
            "createOnlyProperties": ["/properties/foo", "/properties/bar"],
        }
    )

    assert resource_client.has_only_writable_identifiers()


def test_make_payload(resource_client):
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )

    token = "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2f"
    with patch.object(
        resource_client, "generate_token", return_value=token
    ), patch_creds:
        payload = resource_client._make_payload("CREATE", {"foo": "bar"})

    assert payload == {
        "requestData": {
            "callerCredentials": {},
            "resourceProperties": {"foo": "bar"},
            "previousResourceProperties": None,
            "logicalResourceId": token,
        },
        "region": DEFAULT_REGION,
        "awsAccountId": ACCOUNT,
        "action": "CREATE",
        "bearerToken": token,
        "callbackContext": None,
    }


@pytest.mark.parametrize("action", [Action.READ, Action.LIST])
def test_call_sync(resource_client, action):
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )

    mock_client = resource_client._client
    mock_client.invoke.return_value = {"Payload": StringIO('{"status": "SUCCESS"}')}
    with patch_creds:
        status, response = resource_client.call(action, {"resourceModel": SCHEMA})

    assert status == OperationStatus.SUCCESS
    assert response == {"status": OperationStatus.SUCCESS.value}


def test_call_docker():
    patch_sesh = patch(
        "rpdk.core.contract.resource_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_account = patch(
        "rpdk.core.contract.resource_client.get_account",
        autospec=True,
        return_value=ACCOUNT,
    )
    patch_docker = patch("rpdk.core.contract.resource_client.docker", autospec=True)
    with patch_sesh as mock_create_sesh, patch_docker as mock_docker, patch_creds:
        with patch_account:
            mock_client = mock_docker.from_env.return_value
            mock_sesh = mock_create_sesh.return_value
            mock_sesh.region_name = DEFAULT_REGION
            resource_client = ResourceClient(
                DEFAULT_FUNCTION,
                "url",
                DEFAULT_REGION,
                {},
                EMPTY_OVERRIDE,
                docker_image="docker_image",
                executable_entrypoint="entrypoint",
            )
    response_str = (
        "__CFN_RESOURCE_START_RESPONSE__"
        '{"status": "SUCCESS"}__CFN_RESOURCE_END_RESPONSE__'
    )
    mock_client.containers.run.return_value = str.encode(response_str)
    with patch_creds:
        status, response = resource_client.call("CREATE", {"resourceModel": SCHEMA})

    mock_client.containers.run.assert_called_once()
    assert status == OperationStatus.SUCCESS
    assert response == {"status": OperationStatus.SUCCESS.value}


def test_call_docker_executable_entrypoint_null():
    patch_sesh = patch(
        "rpdk.core.contract.resource_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_account = patch(
        "rpdk.core.contract.resource_client.get_account",
        autospec=True,
        return_value=ACCOUNT,
    )
    patch_docker = patch("rpdk.core.contract.resource_client.docker", autospec=True)
    with patch_sesh as mock_create_sesh, patch_docker, patch_creds:
        with patch_account:
            mock_sesh = mock_create_sesh.return_value
            mock_sesh.region_name = DEFAULT_REGION
            resource_client = ResourceClient(
                DEFAULT_FUNCTION,
                "url",
                DEFAULT_REGION,
                {},
                EMPTY_OVERRIDE,
                docker_image="docker_image",
            )

    try:
        with patch_creds:
            resource_client.call("CREATE", {"resourceModel": SCHEMA})
    except InvalidProjectError:
        pass


@pytest.mark.parametrize("action", [Action.CREATE, Action.UPDATE, Action.DELETE])
def test_call_async(resource_client, action):
    mock_client = resource_client._client

    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )

    mock_client.invoke.side_effect = [
        {"Payload": StringIO('{"status": "IN_PROGRESS", "resourceModel": {"c": 3} }')},
        {"Payload": StringIO('{"status": "SUCCESS"}')},
    ]

    with patch_creds:
        status, response = resource_client.call(action, {})

    assert status == OperationStatus.SUCCESS
    assert response == {"status": OperationStatus.SUCCESS.value}


@pytest.mark.parametrize("action", [Action.CREATE, Action.UPDATE, Action.DELETE])
def test_call_async_write_only_properties_are_removed(resource_client, action):
    mock_client = resource_client._client

    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )

    mock_client.invoke.side_effect = [
        {
            "Payload": StringIO(
                '{"status": "SUCCESS", "resourceModel": {"c": 3, "d": 4} }'
            )
        }
    ]

    resource_client._update_schema(SCHEMA)
    with pytest.raises(AssertionError), patch_creds:
        resource_client.call(action, {})


@pytest.mark.parametrize("action", [Action.CREATE, Action.UPDATE, Action.DELETE])
def test_call_async_write_only_properties_are_not_removed_for_in_progress(
    resource_client, action
):
    mock_client = resource_client._client

    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )

    mock_client.invoke.side_effect = [
        {
            "Payload": StringIO(
                '{"status": "IN_PROGRESS", "resourceModel": {"c": 3, "d": 4} }'
            )
        },
        {"Payload": StringIO('{"status": "SUCCESS"}')},
    ]

    resource_client._update_schema(SCHEMA)
    with patch_creds:
        resource_client.call(action, {})


def test_call_and_assert_success(resource_client):
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    mock_client = resource_client._client
    mock_client.invoke.return_value = {"Payload": StringIO('{"status": "SUCCESS"}')}
    with patch_creds:
        status, response, error_code = resource_client.call_and_assert(
            Action.CREATE, OperationStatus.SUCCESS, {}, None
        )
    assert status == OperationStatus.SUCCESS
    assert response == {"status": OperationStatus.SUCCESS.value}
    assert error_code is None


def test_call_and_assert_failed_invalid_payload(resource_client):
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    mock_client = resource_client._client
    mock_client.invoke.return_value = {"Payload": StringIO("invalid json document")}

    with pytest.raises(ValueError), patch_creds:
        status, response, error_code = resource_client.call_and_assert(
            Action.CREATE, OperationStatus.SUCCESS, {}, None
        )


def test_call_and_assert_failed(resource_client):
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    mock_client = resource_client._client
    mock_client.invoke.return_value = {
        "Payload": StringIO('{"status": "FAILED","errorCode": "NotFound"}')
    }
    with patch_creds:
        status, response, error_code = resource_client.call_and_assert(
            Action.DELETE, OperationStatus.FAILED, {}, None
        )
    assert status == OperationStatus.FAILED
    assert response == {"status": OperationStatus.FAILED.value, "errorCode": "NotFound"}
    assert error_code == HandlerErrorCode.NotFound


def test_call_and_assert_exception_unsupported_status(resource_client):
    mock_client = resource_client._client
    mock_client.invoke.return_value = {
        "Payload": StringIO('{"status": "FAILED","errorCode": "NotFound"}')
    }
    with pytest.raises(ValueError):
        resource_client.call_and_assert(Action.DELETE, "OtherStatus", {}, None)


def test_call_and_assert_exception_assertion_mismatch(resource_client):
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    mock_client = resource_client._client
    mock_client.invoke.return_value = {"Payload": StringIO('{"status": "SUCCESS"}')}
    with pytest.raises(AssertionError), patch_creds:
        resource_client.call_and_assert(Action.CREATE, OperationStatus.FAILED, {}, None)


@pytest.mark.parametrize("status", [OperationStatus.SUCCESS, OperationStatus.FAILED])
def test_assert_in_progress_wrong_status(status):
    with pytest.raises(AssertionError):
        ResourceClient.assert_in_progress(status, {})


def test_assert_in_progress_error_code_set():
    with pytest.raises(AssertionError):
        ResourceClient.assert_in_progress(
            OperationStatus.IN_PROGRESS,
            {"errorCode": HandlerErrorCode.AccessDenied.value},
        )


def test_assert_in_progress_resource_models_set():
    with pytest.raises(AssertionError):
        ResourceClient.assert_in_progress(
            OperationStatus.IN_PROGRESS, {"resourceModels": []}
        )


def test_assert_in_progress_callback_delay_seconds_unset():
    callback_delay_seconds = ResourceClient.assert_in_progress(
        OperationStatus.IN_PROGRESS, {"resourceModels": None}
    )
    assert callback_delay_seconds == 0


def test_assert_in_progress_callback_delay_seconds_set():
    callback_delay_seconds = ResourceClient.assert_in_progress(
        OperationStatus.IN_PROGRESS, {"callbackDelaySeconds": 5}
    )
    assert callback_delay_seconds == 5


@pytest.mark.parametrize(
    "status", [OperationStatus.IN_PROGRESS, OperationStatus.FAILED]
)
def test_assert_success_wrong_status(status):
    with pytest.raises(AssertionError):
        ResourceClient.assert_success(status, {})


def test_assert_success_error_code_set():
    with pytest.raises(AssertionError):
        ResourceClient.assert_success(
            OperationStatus.SUCCESS, {"errorCode": HandlerErrorCode.AccessDenied.value}
        )


def test_assert_success_callback_delay_seconds_set():
    with pytest.raises(AssertionError):
        ResourceClient.assert_success(
            OperationStatus.SUCCESS, {"callbackDelaySeconds": 5}
        )


@pytest.mark.parametrize(
    "status", [OperationStatus.IN_PROGRESS, OperationStatus.SUCCESS]
)
def test_assert_failed_wrong_status(status):
    with pytest.raises(AssertionError):
        ResourceClient.assert_failed(status, {})


def test_assert_failed_error_code_unset():
    with pytest.raises(AssertionError):
        ResourceClient.assert_failed(OperationStatus.FAILED, {})


def test_assert_failed_error_code_invalid():
    with pytest.raises(KeyError):
        ResourceClient.assert_failed(OperationStatus.FAILED, {"errorCode": "XXX"})


def test_assert_failed_callback_delay_seconds_set():
    with pytest.raises(AssertionError):
        ResourceClient.assert_failed(
            OperationStatus.FAILED,
            {
                "errorCode": HandlerErrorCode.AccessDenied.value,
                "callbackDelaySeconds": 5,
            },
        )


def test_assert_failed_resource_models_set():
    with pytest.raises(AssertionError):
        ResourceClient.assert_failed(
            OperationStatus.FAILED,
            {"errorCode": HandlerErrorCode.AccessDenied.value, "resourceModels": []},
        )


def test_assert_failed_returns_error_code():
    error_code = ResourceClient.assert_failed(
        OperationStatus.FAILED, {"errorCode": HandlerErrorCode.AccessDenied.value}
    )
    assert error_code == HandlerErrorCode.AccessDenied


def test_override_properties():
    document = {
        "foo": "bar",
        "spam": "eggs",
        "one": "two",
        "array": ["first", "second"],
    }
    override_properties(
        document,
        {("foo",): "baz", ("spam",): {}, ("not_found",): None, ("array", "1"): "last"},
    )
    assert document == {
        "foo": "baz",
        "spam": {},
        "one": "two",
        "array": ["first", "last"],
    }


def test_has_update_handler(resource_client):
    schema = {"handlers": {"update": {"permissions": ["permission"]}}}
    resource_client._update_schema(schema)
    assert resource_client.has_update_handler()


@pytest.mark.parametrize("action", [Action.CREATE, Action.UPDATE, Action.DELETE])
def test_assert_CUD_time(resource_client, action):
    resource_client.assert_time(time.time() - 59, time.time(), action)


@pytest.mark.parametrize("action", [Action.READ, Action.LIST])
def test_assert_RL_time(resource_client, action):
    resource_client.assert_time(time.time() - 29, time.time(), action)


@pytest.mark.parametrize("action", [Action.CREATE, Action.UPDATE, Action.DELETE])
def test_assert_CUD_time_fail(resource_client, action):
    with pytest.raises(AssertionError):
        resource_client.assert_time(time.time() - 61, time.time(), action)


@pytest.mark.parametrize("action", [Action.READ, Action.LIST])
def test_assert_RL_time_fail(resource_client, action):
    with pytest.raises(AssertionError):
        resource_client.assert_time(time.time() - 31, time.time(), action)


def test_assert_primary_identifier_success(resource_client):
    resource_client._update_schema(SCHEMA)
    resource_client.assert_primary_identifier(
        resource_client.primary_identifier_paths, {"a": 1, "b": 2, "c": 3}
    )


def test_assert_primary_identifier_fail(resource_client):
    with pytest.raises(AssertionError):
        resource_client._update_schema(SCHEMA)
        resource_client.assert_primary_identifier(
            resource_client.primary_identifier_paths, {"a": 1, "b": 2}
        )


def test_is_primary_identifier_equal_success(resource_client):
    resource_client._update_schema(SCHEMA)
    assert resource_client.is_primary_identifier_equal(
        resource_client.primary_identifier_paths,
        {"a": 1, "b": 2, "c": 3},
        {"a": 1, "b": 2, "c": 3},
    )


def test_is_primary_identifier_equal_fail(resource_client):
    resource_client._update_schema(SCHEMA)
    assert not resource_client.is_primary_identifier_equal(
        resource_client.primary_identifier_paths,
        {"a": 1, "b": 2, "c": 3},
        {"a": 1, "b": 2, "c": 4},
    )


def test_is_primary_identifier_equal_fail_key(resource_client):
    with pytest.raises(AssertionError):
        resource_client._update_schema(SCHEMA)
        resource_client.is_primary_identifier_equal(
            resource_client.primary_identifier_paths,
            {"a": 1, "b": 2},
            {"a": 1, "b": 2},
        )


def test_assert_write_only_property_does_not_exist(resource_client):
    schema = {
        "a": {"type": "number", "const": 1},
        "b": {"type": "number", "const": 2},
        "c": {"type": "number", "const": 3},
    }
    resource_client._update_schema(schema)
    resource_client.assert_write_only_property_does_not_exist(schema)


@pytest.mark.parametrize("schema", [SCHEMA, SCHEMA_WITH_MULTIPLE_WRITE_PROPERTIES])
def test_assert_write_only_property_does_not_exist_success(resource_client, schema):
    created_resource = {"a": None, "b": 2, "c": 3}
    resource_client._update_schema(schema)
    resource_client.assert_write_only_property_does_not_exist(created_resource)


@pytest.mark.parametrize("schema", [SCHEMA, SCHEMA_WITH_MULTIPLE_WRITE_PROPERTIES])
def test_assert_write_only_property_does_not_exist_fail(resource_client, schema):
    with pytest.raises(AssertionError):
        created_resource = {"a": 1, "b": 2, "c": 3, "d": 4}
        resource_client._update_schema(schema)
        resource_client.assert_write_only_property_does_not_exist(created_resource)


def test_generate_create_example_with_inputs(resource_client_inputs):
    assert resource_client_inputs.generate_create_example() == {"a": 1}


def test_generate_invalid_create_example_with_inputs(resource_client_inputs):
    assert resource_client_inputs.generate_invalid_create_example() == {"b": 2}


def test_generate_update_example_with_inputs(resource_client_inputs):
    assert resource_client_inputs.generate_update_example({"a": 1}) == {"a": 2}


def test_generate_invalid_update_example_with_inputs(resource_client_inputs):
    assert resource_client_inputs.generate_invalid_update_example({"a": 1}) == {"b": 2}


def test_generate_update_example_with_primary_identifier(resource_client_inputs_schema):
    created_resource = resource_client_inputs_schema.generate_create_example()
    # adding read only property to denote a realistic scenario
    created_resource["b"] = 2
    updated_resource = resource_client_inputs_schema.generate_update_example(
        created_resource
    )
    assert updated_resource == {"a": 1, "c": 2, "b": 2}


def test_generate_update_example_with_composite_key(
    resource_client_inputs_composite_key,
):
    created_resource = resource_client_inputs_composite_key.generate_create_example()
    created_resource.update({"d": 3})  # mocking value of d as it is a readOnly property
    updated_resource = resource_client_inputs_composite_key.generate_update_example(
        created_resource
    )
    assert updated_resource == {"a": 1, "c": 2, "d": 3}


def test_compare_should_pass(resource_client):
    resource_client._update_schema(SCHEMA_WITH_NESTED_PROPERTIES)
    inputs = {"b": {"d": 1}, "f": [{"d": 1}], "h": [{"d": 1}, {"d": 2}]}

    outputs = {
        "b": {"d": 1, "e": 3},
        "f": [{"d": 1, "e": 2}],
        "h": [{"d": 1, "e": 3}, {"d": 2}],
    }
    resource_client.compare(inputs, outputs)


def test_compare_should_throw_exception(resource_client):
    resource_client._update_schema(SCHEMA_WITH_NESTED_PROPERTIES)
    inputs = {"b": {"d": 1}, "f": [{"d": 1}], "h": [{"d": 1}], "z": 1}

    outputs = {
        "b": {"d": 1, "e": 2},
        "f": [{"d": 1}],
        "h": [{"d": 1}],
    }
    try:
        resource_client.compare(inputs, outputs)
    except AssertionError:
        logging.debug("This test expects Assertion Exception to be thrown")


def test_compare_should_throw_key_error(resource_client):
    resource_client._update_schema(SCHEMA_WITH_NESTED_PROPERTIES)
    inputs = {"b": {"d": 1}, "f": [{"d": 1}], "h": [{"d": 1}]}

    outputs = {"b": {"d": 1, "e": 2}, "f": [{"d": 1, "e": 2}, {"d": 2, "e": 3}]}
    try:
        resource_client.compare(inputs, outputs)
    except AssertionError:
        logging.debug("This test expects Assertion Exception to be thrown")


def test_compare_ordered_list_throws_assertion_exception(resource_client):
    resource_client._update_schema(SCHEMA_WITH_NESTED_PROPERTIES)
    inputs = {"b": {"d": 1}, "f": [{"d": 1}], "h": [{"d": 1}]}

    outputs = {"b": {"d": 1, "e": 2}, "f": [{"e": 2}, {"d": 2, "e": 3}]}
    try:
        resource_client.compare(inputs, outputs)
    except AssertionError:
        logging.debug("This test expects Assertion Exception to be thrown")
