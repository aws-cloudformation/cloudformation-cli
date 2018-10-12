import json
import time
from collections import deque
from pprint import pprint
from uuid import uuid4

import pytest
from pytest_localserver.http import Request, Response, WSGIServer

from .lambda_transport import LocalLambdaTransport

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

TEST_RESOURCE = {
    "Type": "AWS::S3:Bucket",
    "Resources": {
        "BucketName": "MyBucket",
        "BucketEncryption": {
            "ServerSideEncryptionConfiguration": [
                {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
            ]
        },
    },
}


@pytest.fixture
def transport():
    return LocalLambdaTransport("Handler")


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


def wait_for_specified_events(listener, specified_events, timeout_in_seconds=60):
    events = []
    start_time = time.time()
    terminal = False
    while ((time.time() - start_time) < timeout_in_seconds) and not terminal:
        time.sleep(0.5)
        while listener.events:
            event = listener.events.popleft()
            pprint(event)
            events.append(event)
            if event.get("status", "") in specified_events:
                terminal = True
    return events


def prepare_request(operation, token, resource=None):
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
    return request


def test_create_ack(event_listener, transport):
    token = str(uuid4())
    request = prepare_request(CREATE, token, resource=TEST_RESOURCE)
    transport.send(request, event_listener.server_address)
    events = wait_for_specified_events(event_listener, IN_PROGRESS, ACK_TIMEOUT)

    assert IN_PROGRESS == events[0].get("status")


def test_update_ack(event_listener):
    token = str(uuid4())
    request = prepare_request(UPDATE, token, resource=TEST_RESOURCE)
    transport.send(request, event_listener.server_address)
    events = wait_for_specified_events(event_listener, IN_PROGRESS, ACK_TIMEOUT)

    assert IN_PROGRESS == events[0].get("status")


def test_delete_ack(event_listener):
    token = str(uuid4())
    request = prepare_request(DELETE, token, resource=TEST_RESOURCE)
    transport.send(request, event_listener.server_address)
    events = wait_for_specified_events(event_listener, IN_PROGRESS, ACK_TIMEOUT)

    assert IN_PROGRESS == events[0].get("status")


def test_create(event_listener, transport):
    token = str(uuid4())
    request = prepare_request(CREATE, token, resource=TEST_RESOURCE)
    transport.send(request, event_listener.server_address)
    events = wait_for_specified_events(event_listener, (COMPLETE, FAILED))

    assert COMPLETE == events[-1].get("status")
    assert TEST_RESOURCE == events[-1].get("resources")[0]


def test_read(event_listener):
    token = str(uuid4())
    request = prepare_request(READ, token)
    transport.send(request, event_listener.server_address)
    events = wait_for_specified_events(event_listener, (COMPLETE, FAILED))

    assert COMPLETE == events[-1].get("status")
    assert NOT_FOUND == events[-1].get("errorCode")
    assert TEST_RESOURCE == events[-1].get("resources")[0]


def test_update(event_listener):
    token = str(uuid4())
    request = prepare_request(UPDATE, token, resource=TEST_RESOURCE)
    transport.send(request, event_listener.server_address)
    events = wait_for_specified_events(event_listener, (COMPLETE, FAILED))

    assert COMPLETE == events[-1].get("status")
    assert NOT_FOUND == events[-1].get("errorCode")
    assert TEST_RESOURCE == events[-1].get("resources")[0]


def test_delete(event_listener):
    token = str(uuid4())
    request = prepare_request(DELETE, token, resource=TEST_RESOURCE)
    transport.send(request, event_listener.server_address)
    events = wait_for_specified_events(event_listener, (COMPLETE, FAILED))

    assert COMPLETE == events[-1].get("status")
    assert NOT_FOUND == events[-1].get("errorCode")
    assert TEST_RESOURCE == events[-1].get("resources")[0]


def test_list_empty(event_listener):
    token = str(uuid4())
    request = prepare_request(LIST, token)
    response = transport.send(request, event_listener.server_address)
    assert response["status"] == COMPLETE
    assert response["resources"] == []
