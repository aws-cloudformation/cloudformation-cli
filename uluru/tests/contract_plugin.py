import pytest


class ContractPlugin:
    def __init__(self, transport, test_resource):
        self._transport = transport
        self._test_resource = test_resource

    @pytest.fixture
    def test_resource(self):
        return self._test_resource

    @pytest.fixture
    def transport(self):
        return self._transport
