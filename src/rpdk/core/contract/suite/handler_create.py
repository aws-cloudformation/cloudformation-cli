# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import logging

import pytest

# WARNING: contract tests should use fully qualified imports to avoid issues
# when being loaded by pytest
from rpdk.core.contract.interface import Action, HandlerErrorCode, OperationStatus
from rpdk.core.contract.suite.handler_commons import (
    test_list_success,
    test_read_success,
)

LOG = logging.getLogger(__name__)


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


@pytest.mark.create
@pytest.mark.delete
def contract_create_delete(resource_client):
    requested_model = delete_model = resource_client.generate_create_example()
    try:
        _status, response, _error_code = resource_client.call_and_assert(
            Action.CREATE, OperationStatus.SUCCESS, requested_model
        )
        # check response here
        delete_model = response["resourceModel"]
    finally:
        resource_client.call_and_assert(
            Action.DELETE, OperationStatus.SUCCESS, delete_model
        )


@pytest.mark.create
def contract_create_duplicate(created_resource, resource_client):
    _created_model, request = created_resource
    if resource_client.has_writable_identifier():
        pytest.skip(
            "no identifiers are writeable; skipping duplicate-CREATE-failed test"
        )
    LOG.warning(
        "at least one identifier is writeable; "
        "performing duplicate-CREATE-failed test"
    )
    # Should fail, because different clientRequestToken for the same
    # resource model means that the same resource is trying to be
    # created twice.
    _status, _response, error_code = resource_client.call_and_assert(
        Action.CREATE, OperationStatus.FAILED, request
    )
    assert (
        error_code == HandlerErrorCode.AlreadyExists
    ), "creating the same resource should not be possible"


@pytest.mark.create
@pytest.mark.read
def contract_create_read_success(created_resource, resource_client):
    created_model, _request = created_resource
    test_read_success(resource_client, created_model)


@pytest.mark.create
@pytest.mark.list
def contract_create_list_success(created_resource, resource_client):
    created_model, _request = created_resource
    models = test_list_success(resource_client, created_model)
    assert created_model in models
