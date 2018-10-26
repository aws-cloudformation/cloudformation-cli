import pytest


class ContractPlugin:
    def __init__(self, transport, test_resource, test_updated_resource, resource_def):
        self._transport = transport
        self._test_resource = test_resource
        self._test_updated_resource = test_updated_resource
        self._resource_def = resource_def

    @pytest.fixture
    def test_resource(self):
        return self._test_resource

    @pytest.fixture
    def test_updated_resource(self):
        return self._test_updated_resource

    @pytest.fixture
    def transport(self):
        return self._transport

    @pytest.fixture
    def resource_def(self):
        return self._resource_def
