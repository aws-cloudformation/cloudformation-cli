import pytest


def contract_delete_ack(resource_client):
    event = resource_client.send_request_for_ack(resource_client.DELETE)
    assert event["status"] == resource_client.IN_PROGRESS


def contract_delete_create(resource_client, test_resource, created_resource):
    if not resource_client.get_identifier_property(test_resource, writable=True):
        pytest.skip("No writable identifiers")

    delete_terminal_event = resource_client.delete_resource(created_resource)
    assert delete_terminal_event["status"] == resource_client.COMPLETE

    create_terminal_event = resource_client.create_resource(test_resource)
    assert create_terminal_event["status"] == resource_client.COMPLETE


def contract_delete_read(resource_client, created_resource):
    delete_terminal_event = resource_client.delete_resource(created_resource)
    assert delete_terminal_event["status"] == resource_client.COMPLETE

    read_response = resource_client.read_resource(created_resource)
    assert read_response["status"] == resource_client.FAILED
    assert read_response["errorCode"] == resource_client.NOT_FOUND


def contract_delete_update(
    resource_client, test_resource, test_updated_resource, created_resource
):
    delete_terminal_event = resource_client.delete_resource(created_resource)
    assert delete_terminal_event["status"] == resource_client.COMPLETE

    update_terminal_event = resource_client.update_resource(
        test_resource, test_updated_resource
    )
    assert update_terminal_event["status"] == resource_client.FAILED
    assert update_terminal_event["errorCode"] == resource_client.NOT_FOUND


def contract_delete_delete(resource_client, created_resource):
    delete_terminal_event = resource_client.delete_resource(created_resource)
    assert delete_terminal_event["status"] == resource_client.COMPLETE

    second_delete_terminal_event = resource_client.delete_resource(created_resource)
    assert second_delete_terminal_event["status"] == resource_client.FAILED
    assert second_delete_terminal_event["errorCode"] == resource_client.NOT_FOUND
