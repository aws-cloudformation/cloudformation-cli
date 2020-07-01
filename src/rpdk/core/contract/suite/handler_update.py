# fixture and parameter have the same name
# pylint: disable=redefined-outer-name

import pytest

# WARNING: contract tests should use fully qualified imports to avoid issues
# when being loaded by pytest
from rpdk.core.contract.interface import Action, HandlerErrorCode, OperationStatus
from rpdk.core.contract.suite.handler_commons import (
    test_model_in_list,
    test_read_success,
)


@pytest.fixture(scope="module")
def updated_resource(resource_client):
    create_request = model = resource_client.generate_create_example()
    try:
        _status, response, _error = resource_client.call_and_assert(
            Action.CREATE, OperationStatus.SUCCESS, create_request
        )
        created_model = model = response["resourceModel"]
        update_request = resource_client.generate_update_example(created_model)
        _status, response, _error = resource_client.call_and_assert(
            Action.UPDATE, OperationStatus.SUCCESS, update_request, created_model
        )
        updated_model = response["resourceModel"]
        yield create_request, created_model, update_request, updated_model
    finally:
        resource_client.call_and_assert(Action.DELETE, OperationStatus.SUCCESS, model)


@pytest.mark.update
@pytest.mark.read
def contract_update_read_success(updated_resource, resource_client):
    # should be able to use the created model
    # to read since physical resource id is immutable
    _create_request, _created_model, _update_request, updated_model = updated_resource
    assert resource_client.is_primary_identifier_equal(
        resource_client.primary_identifier_paths, _created_model, updated_model
    )
    test_read_success(resource_client, updated_model)


@pytest.mark.update
@pytest.mark.list
def contract_update_list_success(updated_resource, resource_client):
    # should be able to use the created model
    # to read since physical resource id is immutable
    _create_request, _created_model, _update_request, updated_model = updated_resource
    assert resource_client.is_primary_identifier_equal(
        resource_client.primary_identifier_paths, _created_model, updated_model
    )
    assert test_model_in_list(resource_client, updated_model)


@pytest.mark.update
def contract_update_create_only_property(resource_client):

    if resource_client.create_only_paths:
        create_request = resource_client.generate_create_example()
        try:
            _status, response, _error = resource_client.call_and_assert(
                Action.CREATE, OperationStatus.SUCCESS, create_request
            )
            created_model = response["resourceModel"]
            update_request = resource_client.generate_invalid_update_example(
                created_model
            )
            _status, response, _error = resource_client.call_and_assert(
                Action.UPDATE, OperationStatus.FAILED, update_request, created_model
            )
            assert response["message"]
            assert (
                _error == HandlerErrorCode.NotUpdatable
            ), "updating readOnly or createOnly properties should not be possible"
        finally:
            resource_client.call_and_assert(
                Action.DELETE, OperationStatus.SUCCESS, created_model
            )
    else:
        pytest.skip("No createOnly Properties. Skipping test.")


@pytest.mark.update
def contract_update_non_existent_resource(resource_client):
    create_request = resource_client.generate_create_example()
    update_request = resource_client.generate_update_example(create_request)
    _status, response, _error = resource_client.call_and_assert(
        Action.UPDATE, OperationStatus.FAILED, update_request, create_request
    )
    assert response["message"]
    assert (
        _error == HandlerErrorCode.NotFound
    ), "cannot update a resource which does not exist"
