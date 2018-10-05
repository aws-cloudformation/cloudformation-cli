from handler_client import HandlerClient
from pytest_localserver.plugin import httpserver
from pytest import fixture
from time import sleep
import requests

import json

POLL_INTERVAL = .5


# #TODO figure out how to create/require test resource models from provider
@fixture
def handler_resource():
    return {"requestContext": {"resourceType": "", "clientRequestToken": "test"}}


def is_event_terminal(event):
    return event["status"] in ["FAILED", "COMPLETE"]

def get_progress_events(server):
    num_requests = 0
    complete_or_fail_received = False
    progress_events = []
    while not complete_or_fail_received:
        while num_requests == len(server.requests):
            sleep(POLL_INTERVAL)
        print(server.requests[num_requests].data)
        event = json.loads(server.requests[num_requests].data)
        complete_or_fail_received = is_event_terminal(event)
        progress_events.append(event)
    return progress_events


def get_docker_gateway(url):
    parts = url.split(":")
    return "http://host.docker.internal"
    #return "http://54.240.196.171" + ":" + "8000"#parts[-1]

def test_simple_create(httpserver, handler_resource):
    client = HandlerClient("lambda")
    httpserver.serve_content(content=None, code=200, headers=None)
    sleep(5)
    print(httpserver.url)
    handler_resource["commPoint"] = get_docker_gateway(httpserver.url)
    data = client.create(handler_resource)
    #events = get_progress_events(httpserver)






