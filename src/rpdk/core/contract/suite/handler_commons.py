import logging

from rpdk.core.contract.interface import Action, HandlerErrorCode, OperationStatus

LOG = logging.getLogger(__name__)


def test_create_success(resource_client, current_resource_model):
    _status, response, _error_code = resource_client.call_and_assert(
        Action.CREATE, OperationStatus.SUCCESS, current_resource_model
    )
    resource_client.assert_primary_identifier(
        resource_client.primary_identifier_paths, response["resourceModel"]
    )
    resource_client.assert_write_only_property_does_not_exist(response["resourceModel"])
    return response


def test_create_failure_if_repeat_writeable_id(resource_client, current_resource_model):
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


def test_read_success(resource_client, current_resource_model):
    _status, response, _error_code = resource_client.call_and_assert(
        Action.READ, OperationStatus.SUCCESS, current_resource_model
    )
    assert response["resourceModel"] == current_resource_model
    resource_client.assert_primary_identifier(
        resource_client.primary_identifier_paths, response["resourceModel"]
    )
    resource_client.assert_write_only_property_does_not_exist(response["resourceModel"])
    return response


def test_read_failure_not_found(resource_client, current_resource_model):
    _status, _response, error_code = resource_client.call_and_assert(
        Action.READ, OperationStatus.FAILED, current_resource_model
    )
    assert error_code == HandlerErrorCode.NotFound


def get_resource_model_list(resource_client, current_resource_model):
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
        next_token = next_response.get("nextToken")
    return resource_models


def test_model_in_list(resource_client, current_resource_model):
    resource_models = get_resource_model_list(resource_client, current_resource_model)
    return any(
        resource_client.is_primary_identifier_equal(
            resource_client.primary_identifier_paths,
            resource_model,
            current_resource_model,
        )
        for resource_model in resource_models
    )


def test_update_success(resource_client, update_model, current_model):
    _status, response, _error_code = resource_client.call_and_assert(
        Action.UPDATE, OperationStatus.SUCCESS, update_model, current_model
    )
    resource_client.assert_write_only_property_does_not_exist(response["resourceModel"])
    # The response model should be the same as the create output model,
    # except the update-able properties should be overridden.
    assert response["resourceModel"] == {**current_model, **update_model}
    return response


def test_update_failure_not_found(resource_client, current_resource_model):
    update_model = resource_client.generate_update_example(current_resource_model)
    _status, _response, error_code = resource_client.call_and_assert(
        Action.UPDATE, OperationStatus.FAILED, update_model, current_resource_model
    )
    assert error_code == HandlerErrorCode.NotFound


def test_delete_success(resource_client, current_resource_model):
    _status, response, _error_code = resource_client.call_and_assert(
        Action.DELETE, OperationStatus.SUCCESS, current_resource_model
    )
    return response


def test_delete_failure_not_found(resource_client, current_resource_model):
    _status, _response, error_code = resource_client.call_and_assert(
        Action.DELETE, OperationStatus.FAILED, current_resource_model
    )
    assert error_code == HandlerErrorCode.NotFound
