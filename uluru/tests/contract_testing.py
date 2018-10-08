import json
import time
from collections import deque
from pprint import pprint
from uuid import uuid4

import pytest
from pytest_localserver.http import Request, Response, WSGIServer

from uluru.tests.handler_client import HandlerClient


@pytest.fixture
def event_listener(request):
    server = CallbackServer()
    server.start()
    request.addfinalizer(server.stop)
    return server


class CallbackServer(WSGIServer):
    def __init__(self, host="127.0.0.1", port=0, ssl_context=None):
        super().__init__(host, port, self, ssl_context=ssl_context)
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


def test_simple_create(event_listener):
    client = HandlerClient("lambda")
    _, port = event_listener.server_address
    url = "http://host.docker.internal:{}".format(port)
    token = str(uuid4())
    request = {
        "requestContext": {
            "resourceType": "Dev::Test::Resource",
            "clientRequestToken": token,
            "callbackURL": url,
        }
    }
    client.create(request)
    is_complete, events = wait_for_terminal_event(event_listener)
    assert is_complete
    assert events[0]["status"] == "COMPLETE"
