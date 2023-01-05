from unittest.mock import MagicMock

import pytest

from rpdk.core.contract.contract_plugin import ContractPlugin
from rpdk.core.contract.hook_client import HookClient
from rpdk.core.contract.resource_client import ResourceClient


def test_contract_plugin_no_client():
    plugin_clients = None
    expected_err_msg = "No plugin clients are set up"
    with pytest.raises(RuntimeError) as excinfo:
        ContractPlugin(plugin_clients)

    assert expected_err_msg in str(excinfo.value)

    plugin_clients = {}
    with pytest.raises(RuntimeError) as excinfo:
        ContractPlugin(plugin_clients)

    assert expected_err_msg in str(excinfo.value)


def test_contract_plugin_fixture_resource_client():
    resource_client = MagicMock(spec=ResourceClient)
    plugin_clients = {"resource_client": resource_client}
    plugin = ContractPlugin(plugin_clients)
    assert plugin.resource_client.__wrapped__(plugin) is resource_client


def test_contract_plugin_fixture_resource_client_not_set():
    plugin = ContractPlugin({"client": object()})
    with pytest.raises(ValueError) as excinfo:
        plugin.resource_client.__wrapped__(plugin)
    assert "Contract plugin client not setup for RESOURCE type" in str(excinfo.value)


def test_contract_plugin_fixture_resource_client_invalid():
    plugin = ContractPlugin({"resource_client": object()})
    with pytest.raises(ValueError) as excinfo:
        plugin.resource_client.__wrapped__(plugin)
    assert "Contract plugin client not setup for RESOURCE type" in str(excinfo.value)


def test_contract_plugin_fixture_hook_client():
    hook_client = MagicMock(spec=HookClient)
    plugin_clients = {"hook_client": hook_client}
    plugin = ContractPlugin(plugin_clients)
    assert plugin.hook_client.__wrapped__(plugin) is hook_client


def test_contract_plugin_fixture_hook_client_not_set():
    plugin = ContractPlugin({"client": object()})
    with pytest.raises(ValueError) as excinfo:
        plugin.hook_client.__wrapped__(plugin)
    assert "Contract plugin client not setup for HOOK type" in str(excinfo.value)


def test_contract_plugin_fixture_hook_client_invalid():
    plugin = ContractPlugin({"hook_client": object()})
    with pytest.raises(ValueError) as excinfo:
        plugin.hook_client.__wrapped__(plugin)
    assert "Contract plugin client not setup for HOOK type" in str(excinfo.value)
