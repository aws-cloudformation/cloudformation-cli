import pytest

from rpdk.core.contract.hook_client import HookClient

from .resource_client import ResourceClient


class ContractPlugin:
    def __init__(self, plugin_clients):
        if not plugin_clients:
            raise RuntimeError("No plugin clients are set up")

        self._plugin_clients = plugin_clients

    @pytest.fixture(scope="module")
    def resource_client(self):
        try:
            resource_client = self._plugin_clients["resource_client"]
        except KeyError:
            resource_client = None

        if not isinstance(resource_client, ResourceClient):
            raise ValueError("Contract plugin client not setup for RESOURCE type")

        return resource_client

    @pytest.fixture(scope="module")
    def hook_client(self):
        try:
            hook_client = self._plugin_clients["hook_client"]
        except KeyError:
            hook_client = None

        if not isinstance(hook_client, HookClient):
            raise ValueError("Contract plugin client not setup for HOOK type")

        return hook_client
