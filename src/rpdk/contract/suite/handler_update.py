from .. import contract_utils


def contract_update_ack(event_listener, transport, resource_def):
    request, token = contract_utils.prepare_request(
        contract_utils.UPDATE, resource_def["typeName"]
    )
    transport(request, event_listener.server_address)
    events = contract_utils.wait_for_specified_event(
        event_listener, contract_utils.IN_PROGRESS, contract_utils.ACK_TIMEOUT
    )

    contract_utils.verify_events_contain_token(events, token)
    assert events[0]["status"] == contract_utils.IN_PROGRESS


def contract_update_not_found(
    event_listener, transport, test_resource, test_updated_resource
):
    update_terminal_event = contract_utils.update_resource(
        event_listener, transport, test_resource, test_updated_resource
    )

    assert update_terminal_event["status"] == contract_utils.FAILED
    assert update_terminal_event["errorCode"] == contract_utils.NOT_FOUND


def contract_update_create(
    event_listener, transport, test_resource, test_updated_resource, resource_def
):
    contract_utils.check_for_writable_identifiers(test_resource, resource_def)
    create_terminal_event = contract_utils.create_resource(
        event_listener, transport, test_resource
    )
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == contract_utils.COMPLETE
    contract_utils.compare_requested_model(
        test_resource, created_resource, resource_def
    )

    update_terminal_event = contract_utils.update_resource(
        event_listener, transport, test_resource, test_updated_resource
    )
    updated_resource = update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == contract_utils.COMPLETE
    contract_utils.compare_requested_model(
        test_updated_resource, updated_resource, resource_def
    )

    second_create_terminal_event = contract_utils.create_resource(
        event_listener, transport, test_resource
    )
    assert second_create_terminal_event["status"] == contract_utils.FAILED
    assert second_create_terminal_event["errorCode"] == contract_utils.ALREADY_EXISTS

    delete_terminal_event = contract_utils.delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == contract_utils.COMPLETE


def contract_update_read(
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

    update_terminal_event = contract_utils.update_resource(
        event_listener, transport, test_resource, test_updated_resource
    )
    updated_resource = update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == contract_utils.COMPLETE
    contract_utils.compare_requested_model(
        test_updated_resource, updated_resource, resource_def
    )

    read_response = contract_utils.read_resource(
        event_listener, transport, updated_resource, resource_def
    )
    read_response_resource = read_response["resources"][0]
    assert read_response["status"] == contract_utils.COMPLETE
    assert read_response_resource == updated_resource

    delete_terminal_event = contract_utils.delete_resource(
        event_listener, transport, updated_resource, resource_def
    )
    assert delete_terminal_event["status"] == contract_utils.COMPLETE


def contract_update_update(
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

    update_terminal_event = contract_utils.update_resource(
        event_listener, transport, test_resource, test_updated_resource
    )
    updated_resource = update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == contract_utils.COMPLETE
    contract_utils.compare_requested_model(
        test_updated_resource, updated_resource, resource_def
    )

    second_update_terminal_event = contract_utils.update_resource(
        event_listener, transport, test_updated_resource, test_resource
    )
    second_updated_resource = second_update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == contract_utils.COMPLETE
    contract_utils.compare_requested_model(
        test_resource, second_updated_resource, resource_def
    )

    delete_terminal_event = contract_utils.delete_resource(
        event_listener, transport, updated_resource, resource_def
    )
    assert delete_terminal_event["status"] == contract_utils.COMPLETE
