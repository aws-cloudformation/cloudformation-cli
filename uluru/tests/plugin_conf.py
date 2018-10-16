import pytest


def pytest_collection_modifyitems(items):
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


def pytest_addoption(parser):
    parser.addoption("--transport-type", action="store")
    parser.addoption("--endpoint", action="store")
    parser.addoption("--function-name", action="store")
    parser.addoption("--test-resource", action="store")
