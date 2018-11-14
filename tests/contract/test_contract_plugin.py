from unittest.mock import Mock, patch

import pytest

from rpdk.contract.contract_plugin import ContractPlugin, ResourceFixture
from rpdk.contract.contract_utils import COMPLETE, FAILED, NOT_FOUND, ResourceClient

RESOURCE = {"type": "AWS::Foo::Bar", "properties": {"number": 1}}

CREATE_EVENT = {"status": COMPLETE, "resources": [RESOURCE]}


def test_contract_plugin_fixtures():
    transport = object()
    test_resource = object()
    resource_def = object()
    test_updated_resource = object()
    plugin = ContractPlugin(
        transport, test_resource, test_updated_resource, resource_def
    )
    mock_resource = object()
    with patch("rpdk.contract.contract_plugin.ResourceFixture") as mock_context:
        mock_context.return_value.__enter__.return_value = mock_resource
        assert next(plugin.created_resource.__wrapped__(plugin)) is mock_resource
    assert plugin.test_resource.__wrapped__(plugin) is test_resource
    assert plugin.test_updated_resource.__wrapped__(plugin) is test_updated_resource
    resource_client = plugin.resource_client.__wrapped__(plugin)
    assert resource_client._resource_def is resource_def
    assert resource_client._transport is transport


def test_resource_fixture_success():
    resource_client = ResourceClient(None, None)
    resource_client.create_resource = Mock(return_value=CREATE_EVENT)
    resource_fixture = ResourceFixture(resource_client, RESOURCE)
    resource_client.create_resource.assert_called_once_with(RESOURCE)
    actual_resource = resource_fixture.__enter__()
    resource_client.create_resource.assert_called_once_with(RESOURCE)
    assert actual_resource == CREATE_EVENT["resources"][0]


def test_resource_fixture_create_fail():
    failed_create_event = {"status": FAILED}
    resource_client = ResourceClient(None, None)
    resource_client.create_resource = Mock(return_value=failed_create_event)
    with pytest.raises(AssertionError):
        ResourceFixture(resource_client, RESOURCE)
    resource_client.create_resource.assert_called_once_with(RESOURCE)


@pytest.mark.parametrize(
    "delete_event", [{"status": COMPLETE}, {"status": FAILED, "errorCode": NOT_FOUND}]
)
def test_resource_fixture_delete(delete_event):
    resource_client = ResourceClient(None, None)
    resource_client.create_resource = Mock(return_value=CREATE_EVENT)
    resource_client.delete_resource = Mock(return_value=delete_event)
    resource_fixture = ResourceFixture(resource_client, RESOURCE)
    with resource_fixture:
        pass
    resource_client.create_resource.assert_called_once_with(RESOURCE)
    resource_client.delete_resource.assert_called_once_with(
        CREATE_EVENT["resources"][0]
    )


def test_resource_fixture_delete_fail():
    delete_event = {"status": FAILED, "errorCode": "InternalError"}
    resource_client = ResourceClient(None, None)
    resource_client.create_resource = Mock(return_value=CREATE_EVENT)
    resource_client.delete_resource = Mock(return_value=delete_event)
    resource_fixture = ResourceFixture(resource_client, RESOURCE)
    with pytest.raises(AssertionError):
        with resource_fixture:
            pass
    resource_client.create_resource.assert_called_once_with(RESOURCE)
    resource_client.delete_resource.assert_called_once_with(
        CREATE_EVENT["resources"][0]
    )
