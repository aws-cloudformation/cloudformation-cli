from collections import deque
from unittest.mock import Mock, patch

import pytest
from requests import post

from rpdk.core.contract.contract_utils import (
    COMPLETE,
    CREATE,
    FAILED,
    IN_PROGRESS,
    CallbackServer,
    ResourceClient,
)
from rpdk.core.contract.transports import LocalLambdaTransport
from rpdk.core.jsonutils.pointer import fragment_decode

RESOURCE_MODEL = {"type": "Some::Resource::Type", "properties": {"identifier": "value"}}
UPDATED_RESOURCE_MODEL = {
    "type": "Some::Resource::Type",
    "properties": {"identifier": "new_value"},
}
RESOURCE_DEF = {
    "typeName": "Some::Resource::Type",
    "identifiers": ["#/properties/identifier"],
    "writeOnly": ["#/properties/readOnlyProp"],
    "properties": {
        "identifier": {"type": "string", "description": "Test Identifier"},
        "readOnlyProp": {"type": "string", "description": "Write only property"},
    },
}
EXPECTED_EVENTS = [
    {"status": IN_PROGRESS, "clientRequestToken": "token"},
    {"status": COMPLETE, "clientRequestToken": "token"},
]


@pytest.fixture
def resource_client():
    mock_transport = Mock(spec=LocalLambdaTransport)
    return ResourceClient(mock_transport, RESOURCE_DEF)


def test_send_async_request(resource_client):
    listener_events = deque(EXPECTED_EVENTS)
    mock_listener = Mock(
        spec=CallbackServer, events=listener_events, server_address=("url", "port")
    )
    with patch("rpdk.contract.contract_utils.CallbackServer") as mock_context:
        mock_context.return_value.__enter__.return_value = mock_listener
        returned_events = resource_client.send_async_request(None, "token", COMPLETE)
    assert returned_events == EXPECTED_EVENTS
    resource_client._transport.assert_called_once()


def test_send_sync_request(resource_client):
    resource_client._transport.return_value = EXPECTED_EVENTS[1]
    returned_event = resource_client.send_sync_request(None, "token")
    assert returned_event == EXPECTED_EVENTS[1]
    resource_client._transport.assert_called_once()


def test_prepare_request_all_positional_args(resource_client):
    returned_request, token = resource_client.prepare_request(
        CREATE, resource=UPDATED_RESOURCE_MODEL, previous_resource=RESOURCE_MODEL
    )
    returned_context = returned_request["requestContext"]
    returned_request_data = returned_request["requestData"]
    assert returned_context["operation"] == CREATE
    assert returned_context["resourceType"] == RESOURCE_MODEL["type"]
    assert (
        returned_request_data["resourceProperties"]
        == UPDATED_RESOURCE_MODEL["properties"]
    )
    assert (
        returned_request_data["previousResourceProperties"]
        == RESOURCE_MODEL["properties"]
    )


def test_prepare_request_no_resources(resource_client):
    returned_request, token = resource_client.prepare_request(CREATE, token="token")
    returned_context = returned_request["requestContext"]
    assert returned_context["operation"] == CREATE
    assert returned_context["resourceType"] == RESOURCE_MODEL["type"]
    assert returned_context["clientRequestToken"] == "token"


def test_wait_for_complete_event(resource_client):
    listener_events = deque(EXPECTED_EVENTS)
    mock_listener = Mock(spec=CallbackServer, events=listener_events)
    returned_events = resource_client.wait_for_specified_event(mock_listener, COMPLETE)
    assert returned_events == EXPECTED_EVENTS


def test_wait_for_failed_event(resource_client):
    expected_failed_events = [{"status": IN_PROGRESS}, {"status": FAILED}]
    listener_events = deque(expected_failed_events)
    mock_listener = Mock(spec=CallbackServer, events=listener_events)
    returned_events = resource_client.wait_for_specified_event(mock_listener, COMPLETE)
    assert returned_events == expected_failed_events


def test_verify_events_contain_token_fail(resource_client):
    events = [{"clientRequestToken": "someToken"}]
    with pytest.raises(AssertionError):
        resource_client.verify_events_contain_token(events, "token")


def test_verify_events_contain_token_pass(resource_client):
    events = [{"clientRequestToken": "token"}]
    resource_client.verify_events_contain_token(events, "token")


@pytest.mark.parametrize(
    "async_operation,args",
    [
        (ResourceClient.create_resource, (RESOURCE_MODEL,)),
        (ResourceClient.update_resource, (RESOURCE_MODEL, UPDATED_RESOURCE_MODEL)),
        (ResourceClient.delete_resource, (RESOURCE_MODEL,)),
    ],
)
def test_async_operation(resource_client, async_operation, args):
    resource_client.send_async_request = Mock(return_value=EXPECTED_EVENTS)
    returned_event = async_operation(resource_client, *args)
    resource_client.send_async_request.assert_called_once()
    assert returned_event == EXPECTED_EVENTS[-1]


@pytest.mark.parametrize(
    "sync_operation,args",
    [
        (ResourceClient.read_resource, RESOURCE_MODEL),
        (ResourceClient.list_resources, None),
    ],
)
def test_sync_operation(resource_client, sync_operation, args):
    resource_client.send_sync_request = Mock(return_value=EXPECTED_EVENTS[-1])
    if args:
        returned_event = sync_operation(resource_client, args)
    else:
        returned_event = sync_operation(resource_client)
    resource_client.send_sync_request.assert_called_once()
    assert returned_event == EXPECTED_EVENTS[-1]


def test_send_request_for_ack(resource_client):
    resource_client.send_async_request = Mock(return_value=EXPECTED_EVENTS)
    returned_event = resource_client.send_request_for_ack("SomeOperation")
    assert returned_event == EXPECTED_EVENTS[0]


def test_get_identifier_read_only(resource_client):
    resource_def = RESOURCE_DEF.copy()
    resource_def["readOnly"] = ["#/properties/identifier"]
    resource_client._resource_def = resource_def
    identifier = resource_client.get_identifier_property(RESOURCE_MODEL)
    expected_identifier = fragment_decode(resource_def["readOnly"][0])[-1]
    assert identifier == expected_identifier


def test_get_writable_identifier_none(resource_client):
    resource_def = RESOURCE_DEF.copy()
    resource_def["readOnly"] = ["#/properties/identifier"]
    resource_client._resource_def = resource_def
    identifier = resource_client.get_identifier_property(RESOURCE_MODEL, writable=True)
    assert identifier is None


def test_get_identifier(resource_client):
    identifier = resource_client.get_identifier_property(RESOURCE_MODEL)
    assert identifier == "identifier"


def test_compare_requested_model(resource_client):
    requested_model = RESOURCE_MODEL.copy()
    requested_model["properties"]["readOnlyProp"] = "value"
    resource_client.compare_requested_model(requested_model, RESOURCE_MODEL)


def test_callback_server_valid():
    posted_event = {"event": "test"}
    with CallbackServer() as listener:
        post("http://{}:{}".format(*listener.server_address), json=posted_event)
    recorded_event = listener.events.popleft()
    assert recorded_event == posted_event


def test_callback_server_fail():
    with CallbackServer() as listener:
        post("http://{}:{}".format(*listener.server_address), data="Just Text")
    event = listener.events.popleft()
    assert "callback with invalid content type" in event["error"]
