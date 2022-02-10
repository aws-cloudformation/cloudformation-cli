# fixture and parameter have the same name
# pylint: disable=redefined-outer-name

import pytest

# WARNING: contract tests should use fully qualified imports to avoid issues
# when being loaded by pytest
from rpdk.core.contract.interface import Action, HandlerErrorCode, OperationStatus
from rpdk.core.contract.suite.contract_asserts_commons import failed_event


@pytest.mark.update
@failed_event(
    error_code=HandlerErrorCode.NotFound,
    msg="An update handler MUST return FAILED with a NotFound error code\
         if the resource did not exist prior to the update request",
)
def contract_update_without_create(resource_client):
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
