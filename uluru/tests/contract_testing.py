import json
import time
from collections import deque
from pprint import pprint
from uuid import uuid4

import boto3
import pytest
from botocore import UNSIGNED
from botocore.config import Config
from pytest_localserver.http import Request, Response, WSGIServer


class InvalidTransportTypeError(Exception):
    pass


def transport_lambda(endpoint):
    client = boto3.client(
        "lambda",
        endpoint_url=endpoint,
        use_ssl=False,
        verify=False,
        config=Config(
            signature_version=UNSIGNED,
            read_timeout=5,
            retries={"max_attempts": 0},
            region_name="us-east-1",
        ),
    )

    def call(request_payload):
        response = client.invoke(
            FunctionName="Handler", Payload=json.dumps(request_payload).encode("utf-8")
        )
        return json.load(response["Payload"])

    return call


def transport(transport_type, endpoint):
    if transport_type == "lambda":
        return transport_lambda(endpoint)
    raise InvalidTransportTypeError(
        'Transport Type "{}" is not valid.'.format(transport_type)
    )


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


def wait_for_terminal_event(listener, timeout_in_seconds=60):
    events = []
    start_time = time.time()
    while (time.time() - start_time) < timeout_in_seconds:
        time.sleep(0.5)
        while listener.events:
            event = listener.events.popleft()
            pprint(event)
            events.append(event)
            if event.get("status", "") in ("COMPLETE", "FAILED"):
                return True, events
    return False, events


def prepare_and_send_request(server, operation):
    _, port = server.server_address
    transport_local = transport("lambda", "http://127.0.0.1:3001")
    url = "http://host.docker.internal:{}".format(port)
    token = str(uuid4())
    request = {
        "requestContext": {
            "resourceType": "Dev::Test::Resource",
            "operation": operation,
            "clientRequestToken": token,
            "callbackURL": url,
        }
    }
    transport_local(request)
    return wait_for_terminal_event(server)


def test_simple_create(event_listener):
    is_terminated, events = prepare_and_send_request(event_listener, "Create")
    assert is_terminated
    assert events[0]["status"] == "COMPLETE"
