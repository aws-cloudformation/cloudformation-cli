import logging
from unittest.mock import patch

import pytest

import rpdk.core.contract.suite.handler_commons as commons
from rpdk.core.boto_helpers import LOWER_CAMEL_CRED_KEYS
from rpdk.core.test import DEFAULT_FUNCTION, DEFAULT_REGION, empty_override

LOG = logging.getLogger(__name__)
EMPTY_OVERRIDE = empty_override()
ACCOUNT = "11111111"
SCHEMA = {
    "properties": {
        "a": {"type": "string"},
        "b": {"type": "number"},
        "c": {"type": "number"},
        "d": {"type": "number"},
    },
    "readOnlyProperties": ["/properties/b"],
    "createOnlyProperties": ["/properties/c"],
    "primaryIdentifier": ["/properties/c"],
    "writeOnlyProperties": ["/properties/d"],
    "propertyTransform": {"/properties/a": '$join([a, "Test"])'},
}

TRANSFORM_OUTPUT = {"a": "ValueATest", "c": 1}
INPUT = {"a": "ValueA", "c": 1}
INVALID_OUTPUT = {"a": "ValueB", "c": 1}


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
            from rpdk.core.contract.resource_client import ResourceClient

            client = ResourceClient(
                DEFAULT_FUNCTION,
                endpoint,
                DEFAULT_REGION,
                SCHEMA,
                EMPTY_OVERRIDE,
                {
                    "CREATE": {"a": "ValueA", "c": 3},
                    "UPDATE": {"a": "UpdateValueA", "c": 3},
                    "INVALID": {"b": 2, "c": 3},
                },
            )

    mock_sesh.client.assert_called_once_with("lambda", endpoint_url=endpoint)
    mock_creds.assert_called_once_with(mock_sesh, LOWER_CAMEL_CRED_KEYS, None)
    mock_account.assert_called_once_with(mock_sesh, {})

    assert client._function_name == DEFAULT_FUNCTION
    assert client._schema == SCHEMA
    assert client._overrides == EMPTY_OVERRIDE
    assert client.account == ACCOUNT

    return client


def test_transform_model_equal_input_and_output(resource_client):
    input_model = INPUT.copy()
    output_model = INPUT.copy()

    commons.transform_model1(input_model, output_model, resource_client)
    assert input_model == INPUT


def test_transform_model_equal_output(resource_client):
    input_model = INPUT.copy()
    output_model = TRANSFORM_OUTPUT.copy()

    commons.transform_model1(input_model, output_model, resource_client)
    assert input_model == TRANSFORM_OUTPUT


def test_transform_model_unequal_models(resource_client):
    input_model = INPUT.copy()
    output_model = INVALID_OUTPUT.copy()

    commons.transform_model1(input_model, output_model, resource_client)
    assert input_model != output_model
    assert input_model == TRANSFORM_OUTPUT
