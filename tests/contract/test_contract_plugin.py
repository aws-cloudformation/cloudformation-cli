from unittest.mock import Mock, patch

import pytest

from rpdk.core.contract.contract_plugin import ContractPlugin
from rpdk.core.contract.contract_utils import (
    COMPLETE,
    FAILED,
    NOT_FOUND,
    ResourceClient,
)

RESOURCE = {"type": "AWS::Foo::Bar", "properties": {"number": 1}}

CREATE_EVENT = {"status": COMPLETE, "resources": [RESOURCE]}
DELETE_EVENT = {"status": COMPLETE}


def test_contract_plugin_fixtures():
    test_resource = object()
    resource_client = object()
    test_updated_resource = object()
    plugin = ContractPlugin(resource_client, test_resource, test_updated_resource)
    assert plugin.resource_client.__wrapped__(plugin) is resource_client
    assert plugin.test_resource.__wrapped__(plugin) is test_resource
    assert plugin.test_updated_resource.__wrapped__(plugin) is test_updated_resource


def test_contract_plugin_create_from_fixture():
    plugin = ContractPlugin(None, RESOURCE, None)
    patched_context = patch(
        "rpdk.core.contract.contract_plugin.ContractPlugin._created_resource"
    )
    with patched_context as mock_resource:
        next(plugin.created_resource.__wrapped__(plugin))
    mock_resource.assert_called_once()


@pytest.mark.parametrize(
    "delete_event", [{"status": COMPLETE}, {"status": FAILED, "errorCode": NOT_FOUND}]
)
def test_contract_plugin_create_delete_success(delete_event):
    resource_client = Mock(spec=ResourceClient)
    resource_client.create_resource.return_value = CREATE_EVENT
    resource_client.delete_resource.return_value = delete_event
    plugin = ContractPlugin(resource_client, RESOURCE, None)
    with plugin._created_resource() as yielded_resource:
        assert yielded_resource == RESOURCE
    resource_client.create_resource.assert_called_once_with(RESOURCE)
    plugin._resource_client.delete_resource.assert_called_once_with(RESOURCE)


def test_resource_fixture_create_fail():
    failed_create_event = {"status": FAILED}
    resource_client = Mock(spec=ResourceClient)
    resource_client.create_resource.return_value = failed_create_event
    plugin = ContractPlugin(resource_client, RESOURCE, None)
    with pytest.raises(AssertionError):
        with plugin._created_resource():
            pass
    resource_client.create_resource.assert_called_once_with(RESOURCE)


def test_resource_fixture_delete_fail():
    delete_event = {"status": FAILED, "errorCode": "InternalError"}
    resource_client = Mock(spec=ResourceClient)
    resource_client.create_resource.return_value = CREATE_EVENT
    resource_client.delete_resource.return_value = delete_event
    plugin = ContractPlugin(resource_client, RESOURCE, None)
    with pytest.raises(AssertionError):
        with plugin._created_resource():
            pass
    plugin._resource_client.create_resource.assert_called_once_with(RESOURCE)
    plugin._resource_client.delete_resource.assert_called_once_with(RESOURCE)
