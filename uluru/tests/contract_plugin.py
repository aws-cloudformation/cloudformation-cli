import pytest


class ContractPlugin:
    def __init__(self, transport, test_resource):
        self._transport = transport
        self._test_resource = test_resource

    def pytest_collection_modifyitems(self, items):
        for item in items:
            if "create" in item.nodeid:
                item.add_marker(pytest.mark.create)
            elif "read" in item.nodeid:
                item.add_marker(pytest.mark.read)
            elif "update" in item.nodeid:
                item.add_marker(pytest.mark.update)
            elif "delete" in item.nodeid:
                item.add_marker(pytest.mark.delete)
            elif "list" in item.nodeid:
                item.add_marker(pytest.mark.list)

    @pytest.fixture
    def test_resource(self):
        return self._test_resource

    @pytest.fixture
    def transport(self):
        return self._transport
