# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import pytest

# WARNING: contract tests should use fully qualified imports to avoid issues
# when being loaded by pytest
from rpdk.core.contract.interface import Action, OperationStatus
from rpdk.core.contract.suite.handler_commons import (
    test_list_success,
    test_read_success,
)


@pytest.fixture(scope="module")
def updated_resource(resource_client):
    request = model = resource_client.generate_create_example()
    try:
        update_request = resource_client.generate_update_example(request)
        resource_client.call_and_assert(Action.CREATE, OperationStatus.SUCCESS, request)
        _status, response, _error = resource_client.call_and_assert(
            Action.UPDATE, OperationStatus.SUCCESS, update_request, request
        )
        model = response["resourceModel"]
        yield model, update_request, request
    finally:
        resource_client.call_and_assert(Action.DELETE, OperationStatus.SUCCESS, model)


@pytest.mark.update
@pytest.mark.read
def contract_update_read_success(updated_resource, resource_client):
    # should be able to use the created model
    # to read since physical resource id is immutable
    updated_model, _updated_request, _request = updated_resource
    test_read_success(resource_client, updated_model)


@pytest.mark.update
@pytest.mark.list
def contract_update_list_success(updated_resource, resource_client):
    # should be able to use the created model
    # to read since physical resource id is immutable
    updated_model, _updated_request, _request = updated_resource
    models = test_list_success(resource_client, updated_model)
    assert updated_model in models
