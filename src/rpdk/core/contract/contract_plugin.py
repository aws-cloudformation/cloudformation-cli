import pytest


class ContractPlugin:
    def __init__(self, resource_client):
        self._resource_client = resource_client

    @pytest.fixture(scope="module")
    def resource_client(self):
        return self._resource_client
