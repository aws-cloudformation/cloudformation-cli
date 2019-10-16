# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import logging

import pytest

# WARNING: contract tests should use fully qualified imports to avoid issues
# when being loaded by pytest
from rpdk.core.contract.interface import Action, HandlerErrorCode, OperationStatus
from rpdk.core.contract.suite.handler_commons import test_list_success

LOG = logging.getLogger(__name__)

# For the below tests, the deleted_model fixture
# is a resource that has been created and deleted


@pytest.fixture(scope="module")
def deleted_resource(resource_client):
    request = model = resource_client.generate_create_example()
    try:
        _status, response, _error = resource_client.call_and_assert(
            Action.CREATE, OperationStatus.SUCCESS, request
        )
        model = response["resourceModel"]
        resource_client.call_and_assert(Action.DELETE, OperationStatus.SUCCESS, model)
        yield model, request
    finally:
        resource_client.call_and_assert(Action.DELETE, OperationStatus.SUCCESS, model)


@pytest.mark.delete
@pytest.mark.read
def contract_delete_read(resource_client, deleted_resource):
    deleted_model, _request = deleted_resource
    _status, _response, error_code = resource_client.call_and_assert(
        Action.READ, OperationStatus.FAILED, deleted_model
    )
    assert error_code == HandlerErrorCode.NotFound


@pytest.mark.delete
@pytest.mark.list
def contract_delete_list(resource_client, deleted_resource):
    # LIST: Should not fail after deletion, since it is a list of all
    #       current resources of the resource type. Deletion should
    #       remove the model from the list, however.

    deleted_model, _request = deleted_resource
    list_models = test_list_success(resource_client, deleted_model)
    assert deleted_model not in list_models


@pytest.mark.delete
@pytest.mark.update
def contract_delete_update(resource_client, deleted_resource):
    deleted_model, request = deleted_resource
    update_model = resource_client.generate_update_example(deleted_model)
    _status, _response, error_code = resource_client.call_and_assert(
        Action.UPDATE, OperationStatus.FAILED, update_model, request
    )
    assert error_code == HandlerErrorCode.NotFound


@pytest.mark.delete
def contract_delete_delete(resource_client, deleted_resource):
    deleted_model, _request = deleted_resource
    _status, _response, error_code = resource_client.call_and_assert(
        Action.DELETE, OperationStatus.FAILED, deleted_model
    )
    assert error_code == HandlerErrorCode.NotFound


@pytest.mark.create
@pytest.mark.delete
def contract_delete_create(resource_client, deleted_resource):
    deleted_model, request = deleted_resource
    _status, response, _error_code = resource_client.call_and_assert(
        Action.CREATE, OperationStatus.SUCCESS, request
    )
    assert deleted_model == response["resourceModel"]
