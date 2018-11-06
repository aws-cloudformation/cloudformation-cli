from unittest.mock import patch

import pytest

from rpdk.contract.contract_plugin import ContractPlugin, ResourceFixture
from rpdk.contract.contract_utils import COMPLETE, FAILED, NOT_FOUND, ResourceClient

CREATE_EVENT = {"status": COMPLETE, "resources": [{"resource": 1}]}


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
    assert plugin.resource_client.__wrapped__(plugin)._resource_def is resource_def
    assert plugin.test_updated_resource.__wrapped__(plugin) is test_updated_resource
    assert plugin.resource_client.__wrapped__(plugin)._transport is transport


def test_resource_fixture_success():
    patch_create = patch(
        "rpdk.contract.contract_utils.ResourceClient.create_resource",
        return_value=CREATE_EVENT,
    )
    with patch_create as mock_create:
        resource_fixture = ResourceFixture(ResourceClient(None, None), None)
    mock_create.assert_called_once_with(None)
    actual_resource = resource_fixture.__enter__()
    assert actual_resource == CREATE_EVENT["resources"][0]


def test_resource_fixture_create_fail():
    failed_create_event = {"status": FAILED}
    patch_create = patch(
        "rpdk.contract.contract_utils.ResourceClient.create_resource",
        return_value=failed_create_event,
    )
    with patch_create as mock_create, pytest.raises(AssertionError):
        ResourceFixture(ResourceClient(None, None), None)
    mock_create.assert_called_once_with(None)


@pytest.mark.parametrize(
    "delete_event", [{"status": COMPLETE}, {"status": FAILED, "errorCode": NOT_FOUND}]
)
def test_resource_fixture_delete(delete_event):
    patch_create = patch(
        "rpdk.contract.contract_utils.ResourceClient.create_resource",
        return_value=CREATE_EVENT,
    )
    patch_delete = patch(
        "rpdk.contract.contract_utils.ResourceClient.delete_resource",
        return_value=delete_event,
    )
    with patch_create, patch_delete as mock_delete:
        resource_fixture = ResourceFixture(ResourceClient(None, None), None)
        with resource_fixture:
            pass
    mock_delete.assert_called_once_with(CREATE_EVENT["resources"][0])


def test_resource_fixture_delete_fail():
    delete_event = {"status": FAILED, "errorCode": "InternalError"}
    patch_create = patch(
        "rpdk.contract.contract_utils.ResourceClient.create_resource",
        return_value=CREATE_EVENT,
    )
    patch_delete = patch(
        "rpdk.contract.contract_utils.ResourceClient.delete_resource",
        return_value=delete_event,
    )
    with patch_create, patch_delete as mock_delete, pytest.raises(AssertionError):
        resource_fixture = ResourceFixture(ResourceClient(None, None), None)
        with resource_fixture:
            pass
    mock_delete.assert_called_once_with(CREATE_EVENT["resources"][0])
