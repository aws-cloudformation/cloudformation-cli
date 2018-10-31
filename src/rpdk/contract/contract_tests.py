# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import json
import time
from collections import deque
from uuid import uuid4

import pytest
from pytest_localserver.http import Request, Response, WSGIServer

from ..jsonutils.pointer import fragment_decode

CREATE = "CREATE"
READ = "READ"
UPDATE = "UPDATE"
DELETE = "DELETE"
LIST = "LIST"
ALREADY_EXISTS = "AlreadyExists"
NOT_UPDATABLE = "NotUpdatable"
NOT_FOUND = "NotFound"
NO_OP = "NoOperationToPerform"
IN_PROGRESS = "IN_PROGRESS"
COMPLETE = "COMPLETE"
FAILED = "FAILED"
ACK_TIMEOUT = 3


@pytest.fixture
def event_listener(request):
    server = CallbackServer()
    server.start()
    request.addfinalizer(server.stop)
    return server


class CallbackServer(WSGIServer):
    def __init__(self, host="127.0.0.1", port=0):
        super().__init__(host, port, self, ssl_context=None)
        self.events = deque()

    @Request.application
    def __call__(self, request):
        assert request.headers.get("content-type") == "application/json"
        self.events.append(json.loads(request.data))
        return Response("", mimetype="application/json")


def get_identifier_property(resource_def, resource_model):
    id_reference = fragment_decode(resource_def["identifiers"][0])
    return id_reference[-1], resource_model["properties"][id_reference[-1]]


def wait_for_specified_event(listener, specified_event, timeout_in_seconds=60):
    events = []
    start_time = time.time()
    specified = False
    while ((time.time() - start_time) < timeout_in_seconds) and not specified:
        time.sleep(0.5)
        while listener.events:
            event = listener.events.popleft()
            events.append(event)
            if event.get("status", "") in (specified_event, FAILED):
                specified = True
    return events


def prepare_request(
    operation, resource_type, token=None, resource=None, previous_resource=None
):
    if not token:
        token = str(uuid4())
    request = {
        "requestContext": {
            "resourceType": resource_type,
            "operation": operation,
            "clientRequestToken": token,
        },
        "requestData": {},
    }
    if resource:
        request["requestData"]["resourceProperties"] = resource["properties"]
    if previous_resource:
        request["requestData"]["previousResourceProperties"] = previous_resource[
            "properties"
        ]
    return request, token


def verify_events_contain_token(events, token):
    assert all(event["clientRequestToken"] == token for event in events)


def create_resource(event_listener, transport, resource):
    request, token = prepare_request(CREATE, resource["type"], resource=resource)
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, COMPLETE)
    verify_events_contain_token(events, token)
    return events[-1]


def read_resource(event_listener, transport, resource, resource_def):
    id_key, id_value = get_identifier_property(resource_def, resource)
    read_resource = {"type": resource["type"]}
    read_resource["properties"] = {id_key: id_value}
    request, token = prepare_request(
        READ, resource_def["typeName"], resource=read_resource
    )
    read_response = transport(request, event_listener.server_address)
    assert read_response["clientRequestToken"] == token
    return read_response


def update_resource(event_listener, transport, resource, updated_resource):
    request, token = prepare_request(
        UPDATE, resource["type"], resource=updated_resource, previous_resource=resource
    )
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, COMPLETE)
    verify_events_contain_token(events, token)
    return events[-1]


def delete_resource(event_listener, transport, resource, resource_def):
    id_key, id_value = get_identifier_property(resource_def, resource)
    request, token = prepare_request(
        DELETE, resource["type"], resource={"properties": {id_key: id_value}}
    )
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, COMPLETE)
    verify_events_contain_token(events, token)
    return events[-1]


def compare_requested_model(requested_model, returned_model, resource_def):
    # Do not need to check write only properties in requested model.
    write_only_properties = {
        fragment_decode(prop)[-1] for prop in resource_def.get("writeOnly", ())
    }
    comparable_properties = (
        set(requested_model["properties"].keys()) - write_only_properties
    )
    for key in comparable_properties:
        assert returned_model["properties"][key] == requested_model["properties"][key]


def check_for_writable_identifiers(test_resource, resource_def):
    # Need to have non readOnly identifiers for this test to be worthwhile,
    # because otherwise tests involving creates after deletes/creates
    # with the same properties is simply creating another resource
    encoded_writable_identifiers = set(resource_def["identifiers"]) - set(
        resource_def["readOnly"]
    )
    writable_identifiers = {
        fragment_decode(identifier)[-1] for identifier in encoded_writable_identifiers
    }
    if not set(test_resource["properties"].keys() & writable_identifiers):
        pytest.skip("No writable identifiers")


def test_create_ack(event_listener, transport, resource_def):
    request, token = prepare_request(CREATE, resource_def["typeName"])
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, IN_PROGRESS, ACK_TIMEOUT)

    verify_events_contain_token(events, token)
    assert events[0]["status"] == IN_PROGRESS


def test_update_ack(event_listener, transport, resource_def):
    request, token = prepare_request(UPDATE, resource_def["typeName"])
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, IN_PROGRESS, ACK_TIMEOUT)

    verify_events_contain_token(events, token)
    assert events[0]["status"] == IN_PROGRESS


def test_delete_ack(event_listener, transport, resource_def):
    request, token = prepare_request(DELETE, resource_def["typeName"])
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, IN_PROGRESS, ACK_TIMEOUT)

    verify_events_contain_token(events, token)
    assert events[0]["status"] == IN_PROGRESS


def test_read_not_found(event_listener, transport, test_resource, resource_def):
    read_response = read_resource(
        event_listener, transport, test_resource, resource_def
    )

    assert read_response["status"] == FAILED
    assert read_response["errorCode"] == NOT_FOUND


def test_update_not_found(
    event_listener, transport, test_resource, test_updated_resource
):
    update_terminal_event = update_resource(
        event_listener, transport, test_resource, test_updated_resource
    )

    assert update_terminal_event["status"] == FAILED
    assert update_terminal_event["errorCode"] == NOT_FOUND


def test_delete_not_found(event_listener, transport, test_resource, resource_def):
    delete_terminal_event = delete_resource(
        event_listener, transport, test_resource, resource_def
    )
    assert delete_terminal_event["status"] == FAILED
    assert delete_terminal_event["errorCode"] == NOT_FOUND


def test_list_empty(event_listener, transport, resource_def):
    request, token = prepare_request(LIST, resource_def["typeName"])
    list_response = transport(request, event_listener.server_address)

    assert list_response["clientRequestToken"] == token
    assert list_response["status"] == COMPLETE
    assert list_response["resources"] == []


def test_create_create(event_listener, transport, test_resource, resource_def):
    check_for_writable_identifiers(test_resource, resource_def)

    create_terminal_event = create_resource(event_listener, transport, test_resource)
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == COMPLETE
    compare_requested_model(test_resource, created_resource, resource_def)

    second_create_terminal_event = create_resource(
        event_listener, transport, test_resource
    )
    assert second_create_terminal_event["status"] == FAILED
    assert second_create_terminal_event["errorCode"] == ALREADY_EXISTS

    delete_terminal_event = delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == COMPLETE


def test_create_read(event_listener, transport, test_resource, resource_def):
    create_terminal_event = create_resource(event_listener, transport, test_resource)
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == COMPLETE
    compare_requested_model(test_resource, created_resource, resource_def)

    read_response = read_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert read_response["status"] == COMPLETE
    assert read_response["resources"][0] == created_resource

    delete_terminal_event = delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == COMPLETE


def test_create_delete(event_listener, transport, test_resource, resource_def):
    create_terminal_event = create_resource(event_listener, transport, test_resource)
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == COMPLETE
    compare_requested_model(test_resource, created_resource, resource_def)

    delete_terminal_event = delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == COMPLETE


def test_create_update_noop(event_listener, transport, test_resource, resource_def):
    create_terminal_event = create_resource(event_listener, transport, test_resource)
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == COMPLETE
    compare_requested_model(test_resource, created_resource, resource_def)

    update_terminal_event = update_resource(
        event_listener, transport, test_resource, test_resource
    )
    assert update_terminal_event["status"] == FAILED
    assert update_terminal_event["errorCode"] == NO_OP

    delete_terminal_event = delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == COMPLETE


def test_create_update(
    event_listener, transport, test_resource, test_updated_resource, resource_def
):
    create_terminal_event = create_resource(event_listener, transport, test_resource)
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == COMPLETE
    compare_requested_model(test_resource, created_resource, resource_def)

    update_terminal_event = update_resource(
        event_listener, transport, test_resource, test_updated_resource
    )
    updated_resource = update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == COMPLETE
    compare_requested_model(test_updated_resource, updated_resource, resource_def)

    delete_terminal_event = delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == COMPLETE


def test_update_create(
    event_listener, transport, test_resource, test_updated_resource, resource_def
):
    check_for_writable_identifiers(test_resource, resource_def)
    create_terminal_event = create_resource(event_listener, transport, test_resource)
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == COMPLETE
    compare_requested_model(test_resource, created_resource, resource_def)

    update_terminal_event = update_resource(
        event_listener, transport, test_resource, test_updated_resource
    )
    updated_resource = update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == COMPLETE
    compare_requested_model(test_updated_resource, updated_resource, resource_def)

    second_create_terminal_event = create_resource(
        event_listener, transport, test_resource
    )
    assert second_create_terminal_event["status"] == FAILED
    assert second_create_terminal_event["errorCode"] == ALREADY_EXISTS

    delete_terminal_event = delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == COMPLETE


def test_update_read(
    event_listener, transport, test_resource, test_updated_resource, resource_def
):
    create_terminal_event = create_resource(event_listener, transport, test_resource)
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == COMPLETE
    compare_requested_model(test_resource, created_resource, resource_def)

    update_terminal_event = update_resource(
        event_listener, transport, test_resource, test_updated_resource
    )
    updated_resource = update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == COMPLETE
    compare_requested_model(test_updated_resource, updated_resource, resource_def)

    read_response = read_resource(
        event_listener, transport, updated_resource, resource_def
    )
    read_response_resource = read_response["resources"][0]
    assert read_response["status"] == COMPLETE
    assert read_response_resource == updated_resource

    delete_terminal_event = delete_resource(
        event_listener, transport, updated_resource, resource_def
    )
    assert delete_terminal_event["status"] == COMPLETE


def test_update_update(
    event_listener, transport, test_resource, test_updated_resource, resource_def
):
    create_terminal_event = create_resource(event_listener, transport, test_resource)
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == COMPLETE
    compare_requested_model(test_resource, created_resource, resource_def)

    update_terminal_event = update_resource(
        event_listener, transport, test_resource, test_updated_resource
    )
    updated_resource = update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == COMPLETE
    compare_requested_model(test_updated_resource, updated_resource, resource_def)

    second_update_terminal_event = update_resource(
        event_listener, transport, test_updated_resource, test_resource
    )
    second_updated_resource = second_update_terminal_event["resources"][0]
    assert update_terminal_event["status"] == COMPLETE
    compare_requested_model(test_resource, second_updated_resource, resource_def)

    delete_terminal_event = delete_resource(
        event_listener, transport, updated_resource, resource_def
    )
    assert delete_terminal_event["status"] == COMPLETE


def test_delete_create(event_listener, transport, test_resource, resource_def):
    check_for_writable_identifiers(test_resource, resource_def)
    create_terminal_event = create_resource(event_listener, transport, test_resource)
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == COMPLETE
    compare_requested_model(test_resource, created_resource, resource_def)
    delete_terminal_event = delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == COMPLETE

    create_terminal_event = create_resource(event_listener, transport, test_resource)
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == COMPLETE

    delete_terminal_event = delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == COMPLETE


def test_delete_read(event_listener, transport, test_resource, resource_def):
    create_terminal_event = create_resource(event_listener, transport, test_resource)
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == COMPLETE
    compare_requested_model(test_resource, created_resource, resource_def)
    delete_terminal_event = delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == COMPLETE

    read_response = read_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert read_response["status"] == FAILED
    assert read_response["errorCode"] == NOT_FOUND


def test_delete_update(
    event_listener, transport, test_resource, test_updated_resource, resource_def
):
    create_terminal_event = create_resource(event_listener, transport, test_resource)
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == COMPLETE
    compare_requested_model(test_resource, created_resource, resource_def)
    delete_terminal_event = delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == COMPLETE

    update_terminal_event = update_resource(
        event_listener, transport, test_resource, test_updated_resource
    )
    assert update_terminal_event["status"] == FAILED
    assert update_terminal_event["errorCode"] == NOT_FOUND


def test_delete_delete(event_listener, transport, test_resource, resource_def):
    create_terminal_event = create_resource(event_listener, transport, test_resource)
    created_resource = create_terminal_event["resources"][0]
    assert create_terminal_event["status"] == COMPLETE
    compare_requested_model(test_resource, created_resource, resource_def)
    delete_terminal_event = delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert delete_terminal_event["status"] == COMPLETE

    compare_requested_model(test_resource, created_resource, resource_def)
    second_delete_terminal_event = delete_resource(
        event_listener, transport, created_resource, resource_def
    )
    assert second_delete_terminal_event["status"] == FAILED
    assert second_delete_terminal_event["errorCode"] == NOT_FOUND
