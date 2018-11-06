import pytest

from .. import contract_utils


def contract_delete_ack(resource_client):
    request, token = resource_client.prepare_request(contract_utils.DELETE)
    events = resource_client.send_async_request(
        request, token, contract_utils.IN_PROGRESS
    )
    assert events[0]["status"] == contract_utils.IN_PROGRESS


def contract_delete_create(resource_client, test_resource, created_resource):
    if resource_client.get_identifier_property(test_resource, writable=True) is None:
        pytest.skip("No writable identifiers")

    delete_terminal_event = resource_client.delete_resource(created_resource)
    assert delete_terminal_event["status"] == contract_utils.COMPLETE

    create_terminal_event = resource_client.create_resource(test_resource)
    assert create_terminal_event["status"] == contract_utils.COMPLETE


def contract_delete_read(resource_client, created_resource):
    delete_terminal_event = resource_client.delete_resource(created_resource)
    assert delete_terminal_event["status"] == contract_utils.COMPLETE

    read_response = resource_client.read_resource(created_resource)
    assert read_response["status"] == contract_utils.FAILED
    assert read_response["errorCode"] == contract_utils.NOT_FOUND


def contract_delete_update(
    resource_client, test_resource, test_updated_resource, created_resource
):
    delete_terminal_event = resource_client.delete_resource(created_resource)
    assert delete_terminal_event["status"] == contract_utils.COMPLETE

    update_terminal_event = resource_client.update_resource(
        test_resource, test_updated_resource
    )
    assert update_terminal_event["status"] == contract_utils.FAILED
    assert update_terminal_event["errorCode"] == contract_utils.NOT_FOUND


def contract_delete_delete(resource_client, created_resource):
    delete_terminal_event = resource_client.delete_resource(created_resource)
    assert delete_terminal_event["status"] == contract_utils.COMPLETE

    second_delete_terminal_event = resource_client.delete_resource(created_resource)
    assert second_delete_terminal_event["status"] == contract_utils.FAILED
    assert second_delete_terminal_event["errorCode"] == contract_utils.NOT_FOUND
