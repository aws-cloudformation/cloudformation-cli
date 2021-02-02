# fixture and parameter have the same name
# pylint: disable=redefined-outer-name

import pytest

# WARNING: contract tests should use fully qualified imports to avoid issues
# when being loaded by pytest
from rpdk.core.contract.interface import Action, HandlerErrorCode, OperationStatus
from rpdk.core.contract.suite.contract_asserts import failed_event


@pytest.mark.update
@failed_event(
    error_code=(HandlerErrorCode.NotUpdatable, HandlerErrorCode.NotFound),
    msg="An update hander MUST return FAILED with a NotUpdatable error code \
        if the difference between the previous state and the properties included \
            in the request contains a property defined in the createOnlyProperties \
                in the resource schema",
)
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
            _status, response, _error_code = resource_client.call_and_assert(
                Action.UPDATE, OperationStatus.FAILED, update_request, created_model
            )
            assert response[
                "message"
            ], "The progress event MUST return an error message\
                 when the status is failed"
        finally:
            resource_client.call_and_assert(
                Action.DELETE, OperationStatus.SUCCESS, created_model
            )
    else:
        pytest.skip("No createOnly Properties. Skipping test.")


@pytest.mark.update
@failed_event(
    error_code=HandlerErrorCode.NotFound,
    msg="An update handler MUST return FAILED with a NotFound error code\
         if the resource did not exist prior to the update request",
)
def contract_update_non_existent_resource(resource_client):
    create_request = resource_client.generate_create_example()
    update_request = resource_client.generate_update_example(create_request)
    _status, response, _error = resource_client.call_and_assert(
        Action.UPDATE, OperationStatus.FAILED, update_request, create_request
    )
    assert response[
        "message"
    ], "The progress event MUST return an error message\
         when the status is failed"
    return _error
