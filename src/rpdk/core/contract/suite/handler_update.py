# fixture and parameter have the same name
# pylint: disable=redefined-outer-name

import pytest

# WARNING: contract tests should use fully qualified imports to avoid issues
# when being loaded by pytest
from rpdk.core.contract.interface import Action, OperationStatus
from rpdk.core.contract.resource_client import prune_properties_from_model
from rpdk.core.contract.suite.handler_commons import (
    test_input_equals_output,
    test_model_in_list,
    test_read_success,
)


@pytest.fixture(scope="module")
def updated_resource(resource_client):
    create_request = input_model = resource_client.generate_create_example()
    model = {}
    try:
        _status, response, _error = resource_client.call_and_assert(
            Action.CREATE, OperationStatus.SUCCESS, create_request
        )
        created_model = model = response["resourceModel"]
        test_input_equals_output(resource_client, input_model, created_model)

        update_request = resource_client.generate_update_example(created_model)

        updated_input_model = prune_properties_from_model(
            update_request.copy(), resource_client.read_only_paths
        )

        _status, response, _error = resource_client.call_and_assert(
            Action.UPDATE, OperationStatus.SUCCESS, update_request, created_model
        )
        updated_model = response["resourceModel"]
        test_input_equals_output(resource_client, updated_input_model, updated_model)

        # flake8: noqa: B950
        # pylint: disable=C0301
        yield create_request, created_model, update_request, updated_model, updated_input_model
    finally:
        resource_client.call_and_assert(Action.DELETE, OperationStatus.SUCCESS, model)


@pytest.mark.update
@pytest.mark.read
def contract_update_read_success(updated_resource, resource_client):
    # should be able to use the created model
    # to read since physical resource id is immutable
    (
        _create_request,
        _created_model,
        _update_request,
        updated_model,
        updated_input_model,
    ) = updated_resource
    assert resource_client.is_primary_identifier_equal(
        resource_client.primary_identifier_paths, _created_model, updated_model
    ), "The primaryIdentifier returned must match\
         the primaryIdentifier passed into the request"
    read_response = test_read_success(resource_client, updated_model)
    test_input_equals_output(
        resource_client, updated_input_model, read_response["resourceModel"]
    )


@pytest.mark.update
@pytest.mark.list
def contract_update_list_success(updated_resource, resource_client):
    # should be able to use the created model
    # to read since physical resource id is immutable
    (
        _create_request,
        _created_model,
        _update_request,
        updated_model,
        _updated_input_model,
    ) = updated_resource
    assert resource_client.is_primary_identifier_equal(
        resource_client.primary_identifier_paths, _created_model, updated_model
    ), "The primaryIdentifier returned must match\
         the primaryIdentifier passed into the request"
    assert test_model_in_list(
        resource_client, updated_model
    ), "A list handler MUST always return an updated model"
