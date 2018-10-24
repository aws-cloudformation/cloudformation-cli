# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import json
import time
from collections import deque
from uuid import uuid4

import pytest
from pytest_localserver.http import Request, Response, WSGIServer

from uluru.jsonutils import pointer

CREATE = "CREATE"
READ = "READ"
UPDATE = "UPDATE"
DELETE = "DELETE"
LIST = "LIST"
ALREADY_EXISTS = "AlreadyExists"
NOT_FOUND = "NotFound"
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


def get_identifier_property(definition, resource_model):
    id_reference = pointer.fragment_decode(definition["identifiers"][1])
    return id_reference[-1], resource_model[id_reference[-1]]


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


def prepare_request(operation, resource_type, token=None, resource=None):
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
        request["requestData"]["resourceProperties"] = resource
    return request, token


def verify_events_contain_token(events, token):
    assert all(event["clientRequestToken"] == token for event in events)


def delete_resource(listener, transport, resource, definition):
    id_key, id_value = get_identifier_property(definition, resource)
    delete_request, _token = prepare_request(
        DELETE, definition["typeName"], resource={id_key: id_value}
    )
    transport(delete_request, listener.server_address)
    delete_events = wait_for_specified_event(listener, COMPLETE)
    assert delete_events[-1].get("status") == COMPLETE


def compare_requested_model(requested_model, returned_model, definition):
    write_only_props = []
    if definition.get("writeOnly"):
        for prop in definition["writeOnly"]:
            write_only_props.append(pointer.fragment_decode(prop)[-1])
    for key in requested_model:
        if key not in write_only_props:
            assert returned_model[key] == requested_model[key]


def create_and_delete_resource(listener, transport, resource, definition):
    create_request, token = prepare_request(
        CREATE, definition["typeName"], resource=resource
    )
    transport(create_request, listener.server_address)
    create_events = wait_for_specified_event(listener, COMPLETE)
    last_event = create_events[-1]

    verify_events_contain_token(create_events, token)
    assert COMPLETE == last_event["status"]
    id_key, id_value = get_identifier_property(definition, resource)

    delete_request, token = prepare_request(
        DELETE, definition["typeName"], resource={id_key: id_value}
    )
    transport(delete_request, listener.server_address)
    delete_events = wait_for_specified_event(listener, COMPLETE)

    verify_events_contain_token(delete_events, token)
    assert delete_events[-1].get("status") == COMPLETE
    return last_event["resources"][0]


def test_create_ack(event_listener, transport, resource_def):
    request, token = prepare_request(CREATE, resource_def["typeName"])
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, IN_PROGRESS, ACK_TIMEOUT)

    verify_events_contain_token(events, token)
    assert events[0]["status"] == IN_PROGRESS


def test_update_ack(event_listener, transport, test_resource, resource_def):
    request, token = prepare_request(
        UPDATE, resource_def["typeName"], resource=test_resource
    )
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, IN_PROGRESS, ACK_TIMEOUT)

    verify_events_contain_token(events, token)
    assert events[0]["status"] == IN_PROGRESS


def test_delete_ack(event_listener, transport, test_resource, resource_def):
    request, token = prepare_request(
        DELETE, resource_def["typeName"], resource=test_resource
    )
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, IN_PROGRESS, ACK_TIMEOUT)

    verify_events_contain_token(events, token)
    assert events[0]["status"] == IN_PROGRESS


def test_create(event_listener, transport, test_resource, resource_def):
    request, token = prepare_request(
        CREATE, resource_def["typeName"], resource=test_resource
    )
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, COMPLETE)
    last_event = events[-1]
    created_resource = last_event["resources"][0]

    verify_events_contain_token(events, token)
    assert last_event["status"] == COMPLETE
    compare_requested_model(test_resource, created_resource, resource_def)

    delete_resource(event_listener, transport, created_resource, resource_def)


def test_read_not_found(event_listener, transport, test_resource, resource_def):
    request, token = prepare_request(
        READ, resource_def["typeName"], resource=test_resource
    )
    read_response = transport(request, event_listener.server_address)

    assert read_response["clientRequestToken"] == token
    assert read_response["status"] == FAILED
    assert read_response["errorCode"] == NOT_FOUND


def test_update_not_found(event_listener, transport, test_resource, resource_def):
    request, token = prepare_request(
        UPDATE, resource_def["typeName"], resource=test_resource
    )
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, COMPLETE)
    last_event = events[-1]

    verify_events_contain_token(events, token)
    assert last_event["status"] == FAILED
    assert last_event["errorCode"] == NOT_FOUND


def test_delete_not_found(event_listener, transport, test_resource, resource_def):
    request, token = prepare_request(
        DELETE, resource_def["typeName"], resource=test_resource
    )
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, COMPLETE)
    last_event = events[-1]

    verify_events_contain_token(events, token)
    assert last_event["status"] == FAILED
    assert last_event["errorCode"] == NOT_FOUND


def test_list_empty(event_listener, transport, resource_def):
    request, token = prepare_request(LIST, resource_def["typeName"])
    list_response = transport(request, event_listener.server_address)

    assert list_response["clientRequestToken"] == token
    assert list_response["status"] == COMPLETE
    assert list_response["resources"] == []


def test_create_create(event_listener, transport, test_resource, resource_def):
    id_key = None
    for id_prop in resource_def["identifiers"]:
        if id_prop not in resource_def["readOnly"]:
            id_key = pointer.fragment_decode(id_prop)[-1]
            break
    # only need to check the additional create case
    # if the resource has identifiers that are not readOnly
    if id_key is not None:
        request, _token = prepare_request(
            CREATE, resource_def["typeName"], resource=test_resource
        )
        transport(request, event_listener.server_address)
        create_events = wait_for_specified_event(event_listener, COMPLETE)
        last_event = create_events[-1]
        created_resource = last_event["resources"][0]
        assert COMPLETE == last_event["status"]
        compare_requested_model(test_resource, created_resource, resource_def)

        test_resource[id_key] = created_resource[id_key]
        second_request, second_token = prepare_request(
            CREATE, resource_def["typeName"], resource=test_resource
        )
        transport(second_request, event_listener.server_address)
        second_create_events = wait_for_specified_event(event_listener, COMPLETE)
        verify_events_contain_token(second_create_events, second_token)
        assert FAILED == second_create_events[-1].get("status")
        assert ALREADY_EXISTS == second_create_events[-1].get("errorCode")
        delete_resource(event_listener, transport, created_resource, resource_def)


def test_create_read(event_listener, transport, test_resource, resource_def):
    request, _token = prepare_request(
        CREATE, resource_def["typeName"], resource=test_resource
    )
    transport(request, event_listener.server_address)
    create_events = wait_for_specified_event(event_listener, COMPLETE)
    last_event = create_events[-1]
    created_resource = last_event["resources"][0]

    assert COMPLETE == last_event["status"]
    compare_requested_model(test_resource, created_resource, resource_def)

    id_key, id_value = get_identifier_property(resource_def, created_resource)
    read_request, read_token = prepare_request(
        READ, resource_def["typeName"], resource={id_key: id_value}
    )
    read_response = transport(read_request, event_listener.server_address)

    assert COMPLETE == read_response["status"]
    assert read_token == read_response["clientRequestToken"]
    assert created_resource == read_response["resources"][0]

    delete_resource(event_listener, transport, created_resource, resource_def)


def test_create_delete(event_listener, transport, test_resource, resource_def):
    request, token = prepare_request(
        CREATE, resource_def["typeName"], resource=test_resource
    )
    transport(request, event_listener.server_address)
    create_events = wait_for_specified_event(event_listener, COMPLETE)
    last_event = create_events[-1]
    created_resource = last_event["resources"][0]

    verify_events_contain_token(create_events, token)
    assert COMPLETE == last_event["status"]
    compare_requested_model(test_resource, created_resource, resource_def)

    id_key, id_value = get_identifier_property(resource_def, created_resource)
    delete_request, delete_token = prepare_request(
        DELETE, resource_def["typeName"], resource={id_key: id_value}
    )
    transport(delete_request, event_listener.server_address)
    delete_events = wait_for_specified_event(event_listener, COMPLETE)

    verify_events_contain_token(delete_events, delete_token)
    assert COMPLETE == delete_events[-1]["status"]


def test_delete_create(event_listener, transport, test_resource, resource_def):
    # only need to check creating a resource after deleting
    # if identifier can be included in a create request
    id_key = None
    for id_prop in resource_def["identifiers"]:
        if id_prop not in resource_def["readOnly"]:
            id_key = pointer.fragment_decode(id_prop)[-1]
            break

    if id_key is not None:
        deleted_resource = create_and_delete_resource(
            event_listener, transport, test_resource, resource_def
        )
        test_resource[id_key] = deleted_resource[id_key]
        request, token = prepare_request(
            CREATE, resource_def["typeName"], resource=test_resource
        )
        transport(request, event_listener.server_address)
        events = wait_for_specified_event(event_listener, COMPLETE)
        last_event = events[-1]
        created_resource = last_event["resources"][0]

        compare_requested_model(test_resource, created_resource, resource_def)
        verify_events_contain_token(events, token)
        assert COMPLETE == last_event["status"]

        delete_resource(event_listener, transport, created_resource, resource_def)


def test_delete_read(event_listener, transport, test_resource, resource_def):
    deleted_resource = create_and_delete_resource(
        event_listener, transport, test_resource, resource_def
    )
    id_key, id_value = get_identifier_property(resource_def, deleted_resource)

    request, token = prepare_request(
        READ, resource_def["typeName"], resource={id_key: id_value}
    )
    read_response = transport(request, event_listener.server_address)

    assert read_response["clientRequestToken"] == token
    assert read_response["status"] == FAILED
    assert read_response["errorCode"] == NOT_FOUND


def test_delete_delete(event_listener, transport, test_resource, resource_def):
    deleted_resource = create_and_delete_resource(
        event_listener, transport, test_resource, resource_def
    )
    id_key, id_value = get_identifier_property(resource_def, deleted_resource)

    request, token = prepare_request(
        DELETE, resource_def["typeName"], resource={id_key: id_value}
    )
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, COMPLETE)
    last_event = events[-1]

    verify_events_contain_token(events, token)
    assert last_event["status"] == FAILED
    assert last_event["errorCode"] == NOT_FOUND
