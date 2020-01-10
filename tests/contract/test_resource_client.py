# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,protected-access
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
)
from rpdk.core.test import (
    DEFAULT_ENDPOINT,
    DEFAULT_FUNCTION,
    DEFAULT_REGION,
    empty_override,
)

EMPTY_OVERRIDE = empty_override()


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
    with patch_sesh as mock_create_sesh, patch_creds as mock_creds:
        mock_sesh = mock_create_sesh.return_value
        mock_sesh.region_name = DEFAULT_REGION
        client = ResourceClient(
            DEFAULT_FUNCTION, endpoint, DEFAULT_REGION, {}, EMPTY_OVERRIDE
        )

    mock_sesh.client.assert_called_once_with("lambda", endpoint_url=endpoint)
    mock_creds.assert_called_once_with(mock_sesh, LOWER_CAMEL_CRED_KEYS, None)

    assert client._creds == {}
    assert client._function_name == DEFAULT_FUNCTION
    assert client._schema == {}
    assert client._overrides == EMPTY_OVERRIDE

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


def test_init_sam_cli_client():
    patch_sesh = patch(
        "rpdk.core.contract.resource_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials", autospec=True
    )
    with patch_sesh as mock_create_sesh, patch_creds as mock_creds:
        mock_sesh = mock_create_sesh.return_value
        mock_sesh.region_name = DEFAULT_REGION
        ResourceClient(
            DEFAULT_FUNCTION, DEFAULT_ENDPOINT, DEFAULT_REGION, {}, EMPTY_OVERRIDE
        )

    mock_sesh.client.assert_called_once_with(
        "lambda", endpoint_url=DEFAULT_ENDPOINT, use_ssl=False, verify=False, config=ANY
    )
    mock_creds.assert_called_once_with(mock_sesh, LOWER_CAMEL_CRED_KEYS, None)


def test_generate_token():
    token = ResourceClient.generate_token()
    assert isinstance(token, str)
    assert len(token) == 36


def test_make_request():
    desired_resource_state = object()
    previous_resource_state = object()
    token = object()
    request = ResourceClient.make_request(
        desired_resource_state, previous_resource_state, clientRequestToken=token
    )
    assert request == {
        "desiredResourceState": desired_resource_state,
        "previousResourceState": previous_resource_state,
        "logicalResourceIdentifier": None,
        "clientRequestToken": token,
    }


def test__update_schema(resource_client):
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
    assert resource_client._primary_identifier_paths == {("properties", "a")}
    assert resource_client.read_only_paths == {("properties", "b")}
    assert resource_client._write_only_paths == {("properties", "c")}
    assert resource_client._create_only_paths == {("properties", "d")}


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


def test_has_writable_identifier_primary_is_read_only(resource_client):
    resource_client._update_schema(
        {
            "primaryIdentifier": ["/properties/foo"],
            "readOnlyProperties": ["/properties/foo"],
        }
    )

    assert not resource_client.has_writable_identifier()


def test_has_writable_identifier_primary_is_writeable(resource_client):
    resource_client._update_schema({"primaryIdentifier": ["/properties/foo"]})

    assert resource_client.has_writable_identifier()


def test_has_writable_identifier_primary_and_additional_are_read_only(resource_client):
    resource_client._update_schema(
        {
            "primaryIdentifier": ["/properties/foo"],
            "additionalIdentifiers": [["/properties/bar"]],
            "readOnlyProperties": ["/properties/foo", "/properties/bar"],
        }
    )

    assert not resource_client.has_writable_identifier()


def test_has_writable_identifier_additional_is_writeable(resource_client):
    resource_client._update_schema(
        {
            "primaryIdentifier": ["/properties/foo"],
            "additionalIdentifiers": [["/properties/bar"]],
            "readOnlyProperties": ["/properties/foo"],
        }
    )

    assert resource_client.has_writable_identifier()


def test_has_writable_identifier_compound_is_writeable(resource_client):
    resource_client._update_schema(
        {
            "primaryIdentifier": ["/properties/foo"],
            "additionalIdentifiers": [["/properties/bar", "/properties/baz"]],
            "readOnlyProperties": ["/properties/foo", "/properties/baz"],
        }
    )

    assert resource_client.has_writable_identifier()


def test__make_payload(resource_client):
    resource_client._creds = {}

    token = "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2f"
    with patch.object(resource_client, "generate_token", return_value=token):
        payload = resource_client._make_payload("CREATE", {"foo": "bar"})

    assert payload == {
        "credentials": {},
        "action": "CREATE",
        "request": {"clientRequestToken": token, "foo": "bar"},
        "callbackContext": None,
    }


@pytest.mark.parametrize("action", [Action.READ, Action.LIST])
def test_call_sync(resource_client, action):
    mock_client = resource_client._client

    mock_client.invoke.return_value = {"Payload": StringIO('{"status": "SUCCESS"}')}
    status, response = resource_client.call(action, {})

    assert status == OperationStatus.SUCCESS
    assert response == {"status": OperationStatus.SUCCESS.value}


@pytest.mark.parametrize("action", [Action.CREATE, Action.UPDATE, Action.DELETE])
def test_call_async(resource_client, action):
    mock_client = resource_client._client

    mock_client.invoke.side_effect = [
        {"Payload": StringIO('{"status": "IN_PROGRESS"}')},
        {"Payload": StringIO('{"status": "SUCCESS"}')},
    ]
    status, response = resource_client.call(action, {})

    assert status == OperationStatus.SUCCESS
    assert response == {"status": OperationStatus.SUCCESS.value}


def test_call_and_assert_success(resource_client):
    mock_client = resource_client._client
    mock_client.invoke.return_value = {"Payload": StringIO('{"status": "SUCCESS"}')}
    status, response, error_code = resource_client.call_and_assert(
        Action.CREATE, OperationStatus.SUCCESS, {}, None
    )
    assert status == OperationStatus.SUCCESS
    assert response == {"status": OperationStatus.SUCCESS.value}
    assert error_code is None


def test_call_and_assert_failed(resource_client):
    mock_client = resource_client._client
    mock_client.invoke.return_value = {
        "Payload": StringIO('{"status": "FAILED","errorCode": "NotFound"}')
    }
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
    mock_client = resource_client._client
    mock_client.invoke.return_value = {"Payload": StringIO('{"status": "SUCCESS"}')}
    with pytest.raises(AssertionError):
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


def test_assert_success_callback_context_set():
    with pytest.raises(AssertionError):
        ResourceClient.assert_success(OperationStatus.SUCCESS, {"callbackContext": []})


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


def test_assert_failed_resource_model_set():
    with pytest.raises(AssertionError):
        ResourceClient.assert_failed(
            OperationStatus.FAILED,
            {
                "errorCode": HandlerErrorCode.AccessDenied.value,
                "resourceModel": {"a": 1},
            },
        )


def test_assert_failed_resource_models_set():
    with pytest.raises(AssertionError):
        ResourceClient.assert_failed(
            OperationStatus.FAILED,
            {"errorCode": HandlerErrorCode.AccessDenied.value, "resourceModels": []},
        )


def test_assert_failed_callback_context_set():
    with pytest.raises(AssertionError):
        ResourceClient.assert_failed(
            OperationStatus.FAILED,
            {"errorCode": HandlerErrorCode.AccessDenied.value, "callbackContext": []},
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
