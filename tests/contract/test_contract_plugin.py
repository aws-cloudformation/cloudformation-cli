from unittest.mock import Mock, patch

import requests
from _pytest.fixtures import FixtureRequest
from pytest import fixture

from rpdk.contract.contract_plugin import ContractPlugin


@fixture
def listener(request):
    return ContractPlugin.event_listener(request)


def test_contract_plugin_fixtures():
    transport = object()
    test_resource = object()
    resource_def = object()
    test_updated_resource = object()
    plugin = ContractPlugin(
        transport, test_resource, test_updated_resource, resource_def
    )
    request = Mock(spec=FixtureRequest)
    request.addfinalizer = Mock(return_value=None)
    with patch("rpdk.contract.contract_plugin.CallbackServer", autospec=True) as server:
        plugin.event_listener(request)
    server.assert_called_once()
    request.addfinalizer.assert_called_once()

    assert plugin.transport.__wrapped__(plugin) is transport
    assert plugin.test_resource.__wrapped__(plugin) is test_resource
    assert plugin.resource_def.__wrapped__(plugin) is resource_def
    assert plugin.test_updated_resource.__wrapped__(plugin) is test_updated_resource


def test_callback_server_valid(listener):
    posted_event = {"event": "test"}
    requests.post("http://{}:{}".format(*listener.server_address), json=posted_event)
    recorded_event = listener.events.popleft()
    assert recorded_event == posted_event


def test_callback_server_fail(listener):
    response = requests.post(
        "http://{}:{}".format(*listener.server_address), data="Just Text"
    )
    assert "callback with invalid content type" in response.json()["error"]
