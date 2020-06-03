# fixture and parameter have the same name
# pylint: disable=redefined-outer-name

import pytest

# WARNING: contract tests should use fully qualified imports to avoid issues
# when being loaded by pytest
from rpdk.core.contract.interface import Action, OperationStatus
from rpdk.core.contract.suite.handler_commons import (
    get_resource_model_list,
    test_list_success,
    test_read_success,
)


@pytest.fixture(scope="module")
def created_resource(resource_client):
    request = model = resource_client.generate_create_example()
    try:
        _status, response, _error = resource_client.call_and_assert(
            Action.CREATE, OperationStatus.SUCCESS, request
        )
        model = response["resourceModel"]
        yield model, request
    finally:
        resource_client.call_and_assert(Action.DELETE, OperationStatus.SUCCESS, model)


@pytest.mark.list
@pytest.mark.read
def contract_list_read_success(created_resource, resource_client):
    created_model, _request = created_resource
    assert test_list_success(resource_client, created_model)
    test_read_success(resource_client, created_model)


@pytest.mark.list
def contract_list_empty(resource_client):
    model = resource_client.generate_create_example()
    resource_models = get_resource_model_list(resource_client, model)
    if not resource_models:
        _status, response, _error_code = resource_client.call_and_assert(
            Action.LIST, OperationStatus.SUCCESS, model
        )
        assert len(response["resourceModels"]) == 0
    else:
        pytest.skip("Resources exist in the current account")
