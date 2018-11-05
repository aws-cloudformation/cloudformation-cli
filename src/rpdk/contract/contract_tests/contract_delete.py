from .. import contract_utils


def test_delete_ack(event_listener, transport, resource_def):
    request, token = contract_utils.prepare_request(
        contract_utils.DELETE, resource_def["typeName"]
    )
    transport(request, event_listener.server_address)
    events = contract_utils.wait_for_specified_event(
        event_listener, contract_utils.IN_PROGRESS, contract_utils.ACK_TIMEOUT
    )

    contract_utils.verify_events_contain_token(events, token)
    assert events[0]["status"] == contract_utils.IN_PROGRESS


def test_delete_create(event_listener, transport, test_resource, resource_def):
    contract_utils.check_for_writable_identifiers(test_resource, resource_def)
    create_terminal_event = contract_utils.create_resource(
        event_listener, transport, test_resource
    )
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == contract_utils.COMPLETE

    contract_utils.compare_requested_model(
        test_resource, created_resource, resource_def
    )
    delete_terminal_event = contract_utils.delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == contract_utils.COMPLETE

    create_terminal_event = contract_utils.create_resource(
        event_listener, transport, test_resource
    )
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == contract_utils.COMPLETE

    delete_terminal_event = contract_utils.delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == contract_utils.COMPLETE


def test_delete_read(event_listener, transport, test_resource, resource_def):
    create_terminal_event = contract_utils.create_resource(
        event_listener, transport, test_resource
    )
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == contract_utils.COMPLETE

    contract_utils.compare_requested_model(
        test_resource, created_resource, resource_def
    )
    delete_terminal_event = contract_utils.delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == contract_utils.COMPLETE

    read_response = contract_utils.read_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert read_response["status"] == contract_utils.FAILED
    assert read_response["errorCode"] == contract_utils.NOT_FOUND


def test_delete_update(
    event_listener, transport, test_resource, test_updated_resource, resource_def
):
    create_terminal_event = contract_utils.create_resource(
        event_listener, transport, test_resource
    )
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == contract_utils.COMPLETE

    contract_utils.compare_requested_model(
        test_resource, created_resource, resource_def
    )
    delete_terminal_event = contract_utils.delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == contract_utils.COMPLETE

    update_terminal_event = contract_utils.update_resource(
        event_listener, transport, test_resource, test_updated_resource
    )
    assert update_terminal_event["status"] == contract_utils.FAILED
    assert update_terminal_event["errorCode"] == contract_utils.NOT_FOUND


def test_delete_delete(event_listener, transport, test_resource, resource_def):
    create_terminal_event = contract_utils.create_resource(
        event_listener, transport, test_resource
    )
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == contract_utils.COMPLETE

    contract_utils.compare_requested_model(
        test_resource, created_resource, resource_def
    )
    delete_terminal_event = contract_utils.delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == contract_utils.COMPLETE

    contract_utils.compare_requested_model(
        test_resource, created_resource, resource_def
    )
    second_delete_terminal_event = contract_utils.delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert second_delete_terminal_event["status"] == contract_utils.FAILED
    assert second_delete_terminal_event["errorCode"] == contract_utils.NOT_FOUND
