# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import json
import time
from collections import deque
from uuid import uuid4

import pytest
from pytest_localserver.http import Request, Response, WSGIServer

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


def prepare_request(operation, token=None, resource=None):
    if not token:
        token = str(uuid4())
    request = {
        "clientRequestToken": token,
        "requestContext": {
            "resourceType": "Dev::Test::Resource",
            "operation": operation,
        },
    }
    if resource:
        request["model"] = resource
    # TODO wrapping & encypting test data
    return request, token


def verify_events_contain_token(events, token):
    assert all(event["clientRequestToken"] == token for event in events)


def test_create_ack(event_listener, transport, test_resource):
    request, token = prepare_request(CREATE, resource=test_resource)
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, IN_PROGRESS, ACK_TIMEOUT)

    verify_events_contain_token(events, token)
    assert events[0]["status"] == IN_PROGRESS


def test_update_ack(event_listener, transport, test_resource):
    request, token = prepare_request(UPDATE, resource=test_resource)
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, IN_PROGRESS, ACK_TIMEOUT)

    verify_events_contain_token(events, token)
    assert events[0]["status"] == IN_PROGRESS


def test_delete_ack(event_listener, transport, test_resource):
    request, token = prepare_request(DELETE, resource=test_resource)
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, IN_PROGRESS, ACK_TIMEOUT)

    verify_events_contain_token(events, token)
    assert events[0]["status"] == IN_PROGRESS


def test_create(event_listener, transport, test_resource):
    request, token = prepare_request(CREATE, resource=test_resource)
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, COMPLETE)
    actual_event = events[-1]

    verify_events_contain_token(events, token)
    assert actual_event["status"] == COMPLETE
    assert actual_event["resources"][0] == test_resource


def test_read(event_listener, transport):
    request, token = prepare_request(READ)
    read_response = transport(request, event_listener.server_address)

    assert read_response["clientRequestToken"] == token
    assert read_response["status"] == FAILED
    assert read_response["errorCode"] == NOT_FOUND


def test_update(event_listener, transport, test_resource):
    request, token = prepare_request(UPDATE, resource=test_resource)
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, COMPLETE)
    actual_event = events[-1]

    verify_events_contain_token(events, token)
    assert actual_event["status"] == FAILED
    assert actual_event["errorCode"] == NOT_FOUND


def test_delete(event_listener, transport, test_resource):
    request, token = prepare_request(DELETE, resource=test_resource)
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, COMPLETE)
    actual_event = events[-1]

    verify_events_contain_token(events, token)
    assert actual_event["status"] == FAILED
    assert actual_event["errorCode"] == NOT_FOUND


def test_list_empty(event_listener, transport):
    request, token = prepare_request(LIST)
    list_response = transport(request, event_listener.server_address)

    assert list_response["clientRequestToken"] == token
    assert list_response["status"] == COMPLETE
    assert list_response["resources"] == []
