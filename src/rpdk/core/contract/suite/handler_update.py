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
    create_request = resource_client.generate_create_example()
    try:
        _status, response, _error = resource_client.call_and_assert(
            Action.CREATE, OperationStatus.SUCCESS, create_request
        )
        created_model = response["resourceModel"]
        update_request = resource_client.generate_update_example(created_model)
        _status, response, _error = resource_client.call_and_assert(
            Action.UPDATE, OperationStatus.SUCCESS, update_request, created_model
        )
        updated_model = response["resourceModel"]
        yield create_request, created_model, update_request, updated_model
    finally:
        resource_client.call_and_assert(
            Action.DELETE, OperationStatus.SUCCESS, updated_model
        )


@pytest.mark.update
@pytest.mark.read
def contract_update_read_success(updated_resource, resource_client):
    # should be able to use the created model
    # to read since physical resource id is immutable
    _create_request, _created_model, _update_request, updated_model = updated_resource
    test_read_success(resource_client, updated_model)


@pytest.mark.update
@pytest.mark.list
def contract_update_list_success(updated_resource, resource_client):
    # should be able to use the created model
    # to read since physical resource id is immutable
    _create_request, _created_model, _update_request, updated_model = updated_resource
    models = test_list_success(resource_client, updated_model)
    assert updated_model in models
