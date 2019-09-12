import logging

import pytest

# WARNING: contract tests should use fully qualified imports to avoid issues
# when being loaded by pytest
from rpdk.core.contract.interface import Action, HandlerErrorCode, OperationStatus

LOG = logging.getLogger(__name__)


def contract_check_asserts_work():
    message = (
        "Asserts have been stripped. This is unusual, but happens if the "
        "contract tests are compiled to optimized byte code. As a result, the "
        "contract tests will not run correctly. Please raise an issue with "
        "as much information about your system and runtime as possible."
    )
    with pytest.raises(AssertionError):
        assert False  # noqa: B011
        pytest.fail(message)


def contract_crud_exerciser(resource_client):
    create_model = resource_client.generate_create_example()
    # We eventually update the resource under test, but if
    # something goes wrong, we want the delete handler to at
    # least be able to delete with the initial model.
    #
    # We retain the create model as a separate entity because
    # we'll later want to create a new resource from the same
    # model.
    updated_model = create_model

    try:
        create_response = _test_create_success(resource_client, create_model)
        # Update the model to include values generated by the create handler.
        updated_model = create_response["resourceModel"]

        _test_create_failure_if_repeat_writeable_id(resource_client, create_model)

        _test_read_success(resource_client, updated_model)

        list_models = _test_list_success(resource_client, updated_model)

        _test_model_in_resource_models(resource_client, updated_model, list_models)

        update_response = _test_update_success(resource_client, updated_model)

        updated_model = update_response["resourceModel"]

        # Read and list operations should work as expected after an update.
        _test_read_success(resource_client, updated_model)

        list_models = _test_list_success(resource_client, updated_model)

        _test_model_in_resource_models(resource_client, updated_model, list_models)
    finally:
        _test_delete_success(resource_client, updated_model)

    _test_read_failure_not_found(resource_client, updated_model)

    # LIST: Should not fail after deletion, since it is a list of all
    #       current resources of the resource type. Deletion should
    #       remove the model from the list, however.
    list_models = _test_list_success(resource_client, updated_model)
    _test_model_not_in_resource_models(resource_client, updated_model, list_models)

    _test_update_failure_not_found(resource_client, updated_model)
    # DELETE: Should fail with NotFound because we've already deleted the resource.
    _test_delete_failure_not_found(resource_client, create_model)

    new_create_model = create_model
    try:
        # CREATE: Deleting the resource should not result in artifacts that
        #         prevent creation.
        new_create_model = _test_create_success(resource_client, create_model)[
            "resourceModel"
        ]

    finally:
        # DELETE: Deleting a resource should not result in artifacts that
        #         later prohibit deletion.
        _test_delete_success(resource_client, new_create_model)


def _test_create_success(resource_client, current_resource_model):
    _status, response, _error_code = resource_client.call_and_assert(
        Action.CREATE, OperationStatus.SUCCESS, current_resource_model
    )
    return response


def _test_create_failure_if_repeat_writeable_id(
    resource_client, current_resource_model
):
    if resource_client.has_writable_identifier():
        LOG.debug(
            "at least one identifier is writeable; "
            "performing duplicate-CREATE-failed test"
        )
        # Should fail, because different clientRequestToken for the same
        # resource model means that the same resource is trying to be
        # created twice.
        _status, _response, error_code = resource_client.call_and_assert(
            Action.CREATE, OperationStatus.FAILED, current_resource_model
        )
        assert (
            error_code == HandlerErrorCode.AlreadyExists
        ), "creating the same resource should not be possible"

    else:
        LOG.debug("no identifiers are writeable; skipping duplicate-CREATE-failed test")


def _test_read_success(resource_client, current_resource_model):
    _status, response, _error_code = resource_client.call_and_assert(
        Action.READ, OperationStatus.SUCCESS, current_resource_model
    )
    assert response["resourceModel"] == current_resource_model
    return response


def _test_read_failure_not_found(resource_client, current_resource_model):
    _status, _response, error_code = resource_client.call_and_assert(
        Action.READ, OperationStatus.FAILED, current_resource_model
    )
    assert error_code == HandlerErrorCode.NotFound


def _test_list_success(resource_client, current_resource_model):
    _status, response, _error_code = resource_client.call_and_assert(
        Action.LIST, OperationStatus.SUCCESS, current_resource_model
    )
    next_token = response.get("nextToken")
    resource_models = response["resourceModels"]
    while next_token is not None:
        _status, next_response, _error_code = resource_client.call_and_assert(
            Action.LIST,
            OperationStatus.SUCCESS,
            current_resource_model,
            nextToken=next_token,
        )
        resource_models.extend(next_response["resourceModels"])
    return resource_models


def _test_model_in_resource_models(
    resource_client, current_resource_model, resource_models
):
    expected_primary_ids = resource_client.primary_identifiers_for(
        current_resource_model
    )
    actual_primary_ids = [
        resource_client.primary_identifiers_for(model) for model in resource_models
    ]
    assert expected_primary_ids in actual_primary_ids


def _test_model_not_in_resource_models(
    resource_client, current_resource_model, resource_models
):
    expected_primary_ids = resource_client.primary_identifiers_for(
        current_resource_model
    )
    actual_primary_ids = [
        resource_client.primary_identifiers_for(model) for model in resource_models
    ]
    assert expected_primary_ids not in actual_primary_ids


def _test_update_success(resource_client, current_resource_model):
    update_model = resource_client.generate_update_example(current_resource_model)
    _status, response, _error_code = resource_client.call_and_assert(
        Action.UPDATE, OperationStatus.SUCCESS, update_model, current_resource_model
    )
    # The response model should be the same as the create output model,
    # except the update-able properties should be overridden.
    assert response["resourceModel"] == {**current_resource_model, **update_model}
    return response


def _test_update_failure_not_found(resource_client, current_resource_model):
    update_model = resource_client.generate_update_example(current_resource_model)
    _status, _response, error_code = resource_client.call_and_assert(
        Action.UPDATE, OperationStatus.FAILED, update_model, current_resource_model
    )
    assert error_code == HandlerErrorCode.NotFound


def _test_delete_success(resource_client, current_resource_model):
    _status, response, _error_code = resource_client.call_and_assert(
        Action.DELETE, OperationStatus.SUCCESS, current_resource_model
    )
    return response


def _test_delete_failure_not_found(resource_client, current_resource_model):
    _status, _response, error_code = resource_client.call_and_assert(
        Action.DELETE, OperationStatus.FAILED, current_resource_model
    )
    assert error_code == HandlerErrorCode.NotFound
