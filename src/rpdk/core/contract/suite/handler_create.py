import pytest


def contract_create_ack(resource_client):
    event = resource_client.send_request_for_ack(resource_client.CREATE)
    assert event["status"] == resource_client.IN_PROGRESS


@pytest.mark.usefixtures("created_resource")
def contract_create_create(resource_client, test_resource):
    if not resource_client.get_identifier_property(test_resource, writable=True):
        pytest.skip("No writable identifiers")
    second_create_terminal_event = resource_client.create_resource(test_resource)
    assert second_create_terminal_event["status"] == resource_client.FAILED
    assert second_create_terminal_event["errorCode"] == resource_client.ALREADY_EXISTS


def contract_create_update_noop(resource_client, test_resource, created_resource):
    update_terminal_event = resource_client.update_resource(
        created_resource, test_resource
    )
    assert update_terminal_event["status"] == resource_client.FAILED
    assert update_terminal_event["errorCode"] == resource_client.NO_OP


def contract_create_update(resource_client, test_updated_resource, created_resource):
    update_terminal_event = resource_client.update_resource(
        created_resource, test_updated_resource
    )
    updated_resource = update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == resource_client.COMPLETE
    resource_client.compare_requested_model(test_updated_resource, updated_resource)


def contract_create_read(resource_client, created_resource):
    read_response = resource_client.read_resource(created_resource)
    assert read_response["status"] == resource_client.COMPLETE
    assert read_response["resources"][0] == created_resource


def contract_create_delete(resource_client, created_resource, test_resource):
    resource_client.compare_requested_model(test_resource, created_resource)
