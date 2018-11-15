import pytest

from .. import contract_utils


def contract_update_ack(resource_client):
    event = resource_client.send_request_for_ack(contract_utils.UPDATE)
    assert event["status"] == contract_utils.IN_PROGRESS


def contract_update_not_found(resource_client, test_resource, test_updated_resource):
    update_terminal_event = resource_client.update_resource(
        test_resource, test_updated_resource
    )

    assert update_terminal_event["status"] == contract_utils.FAILED
    assert update_terminal_event["errorCode"] == contract_utils.NOT_FOUND


def contract_update_create(
    resource_client, test_resource, test_updated_resource, created_resource
):
    if not resource_client.get_identifier_property(test_resource, writable=True):
        pytest.skip("No writable identifiers")

    update_terminal_event = resource_client.update_resource(
        created_resource, test_updated_resource
    )
    assert update_terminal_event["status"] == contract_utils.COMPLETE

    second_create_terminal_event = resource_client.create_resource(test_resource)
    assert second_create_terminal_event["status"] == contract_utils.FAILED
    assert second_create_terminal_event["errorCode"] == contract_utils.ALREADY_EXISTS


def contract_update_read(resource_client, test_updated_resource, created_resource):
    update_terminal_event = resource_client.update_resource(
        created_resource, test_updated_resource
    )
    updated_resource = update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == contract_utils.COMPLETE

    read_response = resource_client.read_resource(updated_resource)
    read_response_resource = read_response["resources"][0]
    assert read_response["status"] == contract_utils.COMPLETE
    assert read_response_resource == updated_resource


def contract_update_update(
    resource_client, test_resource, test_updated_resource, created_resource
):
    update_terminal_event = resource_client.update_resource(
        created_resource, test_updated_resource
    )
    updated_resource = update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == contract_utils.COMPLETE

    second_update_terminal_event = resource_client.update_resource(
        updated_resource, test_resource
    )
    second_updated_resource = second_update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == contract_utils.COMPLETE
    resource_client.compare_requested_model(test_resource, second_updated_resource)
