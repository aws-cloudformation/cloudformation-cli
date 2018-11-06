from collections import deque
from unittest.mock import Mock, patch

import pytest

import rpdk.contract.contract_utils as utils
from rpdk.contract.contract_plugin import CallbackServer

RESOURCE_MODEL = {"type": "Some::Resource::Type", "properties": {"identifier": "value"}}
UPDATED_RESOURCE_MODEL = {"properties": {"identifier": "newvalue"}}
RESOURCE_DEF = {
    "typeName": "Some::Resource::Type",
    "identifiers": ["#/properties/identifier"],
    "readOnly": ["#/properties/identifier"],
    "writeOnly": ["#/properties/secret"],
    "properties": {
        "identifier": {"type": "string", "description": "Test Identifier"},
        "secret": {"type": "string", "description": "Write only property"},
    },
}
EXPECTED_EVENTS = [
    {"status": utils.IN_PROGRESS, "clientRequestToken": "token"},
    {"status": utils.COMPLETE, "clientRequestToken": "token"},
]


def test_get_identifier_property():
    returned_id, returned_value = utils.get_identifier_property(
        RESOURCE_DEF, RESOURCE_MODEL
    )
    assert returned_id == "identifier"
    assert returned_value == RESOURCE_MODEL["properties"]["identifier"]


def test_prepare_request_all_positional_args():
    returned_request, token = utils.prepare_request(
        utils.CREATE,
        RESOURCE_MODEL["type"],
        resource=UPDATED_RESOURCE_MODEL,
        previous_resource=RESOURCE_MODEL,
    )
    returned_context = returned_request["requestContext"]
    returned_request_data = returned_request["requestData"]
    assert returned_context["operation"] == utils.CREATE
    assert returned_context["resourceType"] == RESOURCE_MODEL["type"]
    assert (
        returned_request_data["resourceProperties"]
        == UPDATED_RESOURCE_MODEL["properties"]
    )
    assert (
        returned_request_data["previousResourceProperties"]
        == RESOURCE_MODEL["properties"]
    )


def test_prepare_request_no_resources():
    returned_request, token = utils.prepare_request(
        utils.CREATE, RESOURCE_MODEL["type"], token="token"
    )
    returned_context = returned_request["requestContext"]
    assert returned_context["operation"] == utils.CREATE
    assert returned_context["resourceType"] == RESOURCE_MODEL["type"]
    assert returned_context["clientRequestToken"] == "token"


def test_wait_for_complete_event():
    listener_events = deque(EXPECTED_EVENTS)
    mock_listener = Mock(spec=CallbackServer, events=listener_events)
    returned_events = utils.wait_for_specified_event(mock_listener, utils.COMPLETE)
    assert returned_events == EXPECTED_EVENTS


def test_wait_for_failed_event():
    expected_failed_events = [{"status": utils.IN_PROGRESS}, {"status": utils.FAILED}]
    listener_events = deque(expected_failed_events)
    mock_listener = Mock(spec=CallbackServer, events=listener_events)
    returned_events = utils.wait_for_specified_event(mock_listener, utils.COMPLETE)
    assert returned_events == expected_failed_events


def test_verify_events_contain_token_fail():
    events = [{"clientRequestToken": "someToken"}]
    with pytest.raises(AssertionError):
        utils.verify_events_contain_token(events, "token")


def test_verify_events_contain_token_pass():
    events = [{"clientRequestToken": "token"}]
    utils.verify_events_contain_token(events, "token")


def test_create_resource():
    listener_events = deque(EXPECTED_EVENTS)
    mock_listener = Mock(
        spec=CallbackServer, events=listener_events, server_address=("url", "port")
    )
    mock_transport = Mock()
    with patch(
        "rpdk.contract.contract_utils.verify_events_contain_token", autospec=True
    ) as verify_token:
        returned_event = utils.create_resource(
            mock_listener, mock_transport, RESOURCE_MODEL
        )
        verify_token.assert_called_once()
        assert returned_event == EXPECTED_EVENTS[-1]


def test_read_resource():
    listener_events = deque(EXPECTED_EVENTS)
    mock_listener = Mock(
        spec=CallbackServer, events=listener_events, server_address=("url", "port")
    )
    mock_transport = Mock(return_value=EXPECTED_EVENTS[1])
    with patch(
        "rpdk.contract.contract_utils.verify_events_contain_token", autospec=True
    ) as verify_token:
        returned_event = utils.read_resource(
            mock_listener, mock_transport, RESOURCE_MODEL, RESOURCE_DEF
        )
        verify_token.assert_called_once()
        assert returned_event == EXPECTED_EVENTS[-1]


def test_update_resource():
    listener_events = deque(EXPECTED_EVENTS)
    mock_listener = Mock(
        spec=CallbackServer, events=listener_events, server_address=("url", "port")
    )
    mock_transport = Mock()
    with patch(
        "rpdk.contract.contract_utils.verify_events_contain_token", autospec=True
    ) as verify_token:
        returned_event = utils.update_resource(
            mock_listener, mock_transport, RESOURCE_MODEL, UPDATED_RESOURCE_MODEL
        )
        verify_token.assert_called_once()
        assert returned_event == EXPECTED_EVENTS[-1]


def test_delete_resource():
    listener_events = deque(EXPECTED_EVENTS)
    mock_listener = Mock(
        spec=CallbackServer, events=listener_events, server_address=("url", "port")
    )
    mock_transport = Mock()
    with patch(
        "rpdk.contract.contract_utils.verify_events_contain_token", autospec=True
    ) as verify_token:
        returned_event = utils.delete_resource(
            mock_listener, mock_transport, RESOURCE_MODEL, RESOURCE_DEF
        )
        verify_token.assert_called_once()
        assert returned_event == EXPECTED_EVENTS[-1]


def test_check_writable_identifiers_skip():
    with patch("pytest.skip") as skip_function:
        utils.check_for_writable_identifiers(RESOURCE_MODEL, RESOURCE_DEF)
        skip_function.assert_called_once()


def test_check_writable_identifiers_no_skip():
    writable_id_resource_def = RESOURCE_DEF.copy()
    writable_id_resource_def["readOnly"] = []
    with patch("pytest.skip") as skip_function:
        utils.check_for_writable_identifiers(RESOURCE_MODEL, writable_id_resource_def)
        skip_function.assert_not_called()


def test_compare_requested_model():
    requested_model = RESOURCE_MODEL.copy()
    requested_model["properties"]["secret"] = "value"
    utils.compare_requested_model(requested_model, RESOURCE_MODEL, RESOURCE_DEF)
