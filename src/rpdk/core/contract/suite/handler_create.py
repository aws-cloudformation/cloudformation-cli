# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import logging

import pytest

# WARNING: contract tests should use fully qualified imports to avoid issues
# when being loaded by pytest
from rpdk.core.contract.interface import Action, HandlerErrorCode, OperationStatus
from rpdk.core.contract.suite.contract_asserts import (
    failed_event,
    skip_not_writable_identifier,
)
from rpdk.core.contract.suite.handler_commons import (
    test_create_failure_if_repeat_writeable_id,
    test_create_success,
    test_delete_success,
    test_input_equals_output,
    test_model_in_list,
    test_read_success,
)

LOG = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def created_resource(resource_client):
    request = input_model = model = resource_client.generate_create_example()
    try:
        _status, response, _error = resource_client.call_and_assert(
            Action.CREATE, OperationStatus.SUCCESS, request
        )
        model = response["resourceModel"]
        test_input_equals_output(resource_client, input_model, model)
        yield input_model, model, request
    finally:
        resource_client.call_and_assert(Action.DELETE, OperationStatus.SUCCESS, model)


@pytest.mark.create
@pytest.mark.delete
def contract_create_delete(resource_client):
    requested_model = (
        delete_model
    ) = input_model = resource_client.generate_create_example()
    try:
        response = test_create_success(resource_client, requested_model)
        # check response here
        delete_model = response["resourceModel"]
        test_input_equals_output(resource_client, input_model, delete_model)
    finally:
        test_delete_success(resource_client, delete_model)


@pytest.mark.create
def contract_invalid_create(resource_client):
    if resource_client.read_only_paths:
        _create_with_invalid_model(resource_client)
    else:
        pytest.skip("No readOnly Properties. Skipping test.")


@failed_event(error_code=HandlerErrorCode.InvalidRequest)
def _create_with_invalid_model(resource_client):
    try:
        requested_model = resource_client.generate_invalid_create_example()
        _status, response, _error_code = resource_client.call_and_assert(
            Action.CREATE, OperationStatus.FAILED, requested_model
        )
        assert response["message"]
        return _error_code
    finally:
        resource_client.call(Action.DELETE, requested_model)


@pytest.mark.create
@skip_not_writable_identifier
def contract_create_duplicate(created_resource, resource_client):
    _input_model, _created_model, request = created_resource
    test_create_failure_if_repeat_writeable_id(resource_client, request)


@pytest.mark.create
@pytest.mark.read
def contract_create_read_success(created_resource, resource_client):
    input_model, created_model, _request = created_resource
    read_response = test_read_success(resource_client, created_model)
    test_input_equals_output(
        resource_client, input_model, read_response["resourceModel"]
    )


@pytest.mark.create
@pytest.mark.list
@pytest.mark.read
def contract_create_list_success(created_resource, resource_client):
    _input_model, created_model, _request = created_resource
    assert test_model_in_list(resource_client, created_model)
    test_read_success(resource_client, created_model)
