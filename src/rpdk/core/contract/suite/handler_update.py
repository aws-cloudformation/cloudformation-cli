import pytest


def contract_update_ack(resource_client):
    event = resource_client.send_request_for_ack(resource_client.UPDATE)
    assert event["status"] == resource_client.IN_PROGRESS


def contract_update_not_found(resource_client, test_resource, test_updated_resource):
    update_terminal_event = resource_client.update_resource(
        test_resource, test_updated_resource
    )

    assert update_terminal_event["status"] == resource_client.FAILED
    assert update_terminal_event["errorCode"] == resource_client.NOT_FOUND


def contract_update_create(
    resource_client, test_resource, test_updated_resource, created_resource
):
    if not resource_client.get_identifier_property(test_resource, writable=True):
        pytest.skip("No writable identifiers")

    update_terminal_event = resource_client.update_resource(
        created_resource, test_updated_resource
    )
    assert update_terminal_event["status"] == resource_client.COMPLETE

    second_create_terminal_event = resource_client.create_resource(test_resource)
    assert second_create_terminal_event["status"] == resource_client.FAILED
    assert second_create_terminal_event["errorCode"] == resource_client.ALREADY_EXISTS


def contract_update_read(resource_client, test_updated_resource, created_resource):
    update_terminal_event = resource_client.update_resource(
        created_resource, test_updated_resource
    )
    updated_resource = update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == resource_client.COMPLETE

    read_response = resource_client.read_resource(updated_resource)
    read_response_resource = read_response["resources"][0]
    assert read_response["status"] == resource_client.COMPLETE
    assert read_response_resource == updated_resource


def contract_update_update(
    resource_client, test_resource, test_updated_resource, created_resource
):
    update_terminal_event = resource_client.update_resource(
        created_resource, test_updated_resource
    )
    updated_resource = update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == resource_client.COMPLETE

    second_update_terminal_event = resource_client.update_resource(
        updated_resource, test_resource
    )
    second_updated_resource = second_update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == resource_client.COMPLETE
    resource_client.compare_requested_model(test_resource, second_updated_resource)
