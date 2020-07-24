# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import logging

import pytest

# WARNING: contract tests should use fully qualified imports to avoid issues
# when being loaded by pytest
from rpdk.core.contract.interface import Action, HandlerErrorCode, OperationStatus
from rpdk.core.contract.resource_client import prune_properties_from_model
from rpdk.core.contract.suite.handler_commons import (
    test_create_success,
    test_delete_failure_not_found,
    test_model_in_list,
    test_read_failure_not_found,
    test_update_failure_not_found,
)

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
        _status, response, _error = resource_client.call_and_assert(
            Action.DELETE, OperationStatus.SUCCESS, model
        )
        assert "resourceModel" not in response
        yield model, request
    finally:
        request = resource_client.make_request(
            model,
            None,
            resource_client.region,
            resource_client.account,
            resource_client.partition,
        )
        status, response = resource_client.call(Action.DELETE, request)

        # a failed status is allowed if the error code is NotFound
        if status == OperationStatus.FAILED:
            error_code = resource_client.assert_failed(status, response)
            assert error_code == HandlerErrorCode.NotFound
        else:
            resource_client.assert_success(status, response)


@pytest.mark.delete
@pytest.mark.read
def contract_delete_read(resource_client, deleted_resource):
    deleted_model, _request = deleted_resource
    test_read_failure_not_found(resource_client, deleted_model)


@pytest.mark.delete
@pytest.mark.list
def contract_delete_list(resource_client, deleted_resource):
    # LIST: Should not fail after deletion, since it is a list of all
    #       current resources of the resource type. Deletion should
    #       remove the model from the list, however.

    deleted_model, _request = deleted_resource
    assert not test_model_in_list(resource_client, deleted_model)


@pytest.mark.delete
@pytest.mark.update
def contract_delete_update(resource_client, deleted_resource):
    deleted_model, _request = deleted_resource
    test_update_failure_not_found(resource_client, deleted_model)


@pytest.mark.delete
def contract_delete_delete(resource_client, deleted_resource):
    deleted_model, _request = deleted_resource
    test_delete_failure_not_found(resource_client, deleted_model)


@pytest.mark.create
@pytest.mark.delete
def contract_delete_create(resource_client, deleted_resource):
    if resource_client.has_writable_identifier():
        deleted_model, request = deleted_resource
        response = test_create_success(resource_client, request)

        # read-only properties should be excluded from the comparison
        prune_properties_from_model(deleted_model, resource_client.read_only_paths)
        prune_properties_from_model(
            response["resourceModel"], resource_client.read_only_paths
        )

        assert deleted_model == response["resourceModel"]
    else:
        pytest.skip("No writable identifiers. Skipping test.")
