import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "create" in item.nodeid:
            item.add_marker(pytest.mark.interface)
        elif "read" in item.nodeid:
            item.add_marker(pytest.mark.event)
        elif "update" in item.nodeid:
            item.add_marker(pytest.mark.event)
        elif "delete" in item.nodeid:
            item.add_marker(pytest.mark.event)
        elif "list" in item.nodeid:
            item.add_marker(pytest.mark.event)


def pytest_addoption(parser):
    parser.addoption(
        "--transport-type", action="store", help="Select a valid transport type"
    )
    parser.addoption("--endpoint", action="store")
    parser.addoption("--function-name", action="store")
    parser.addoption("--test-resource", action="store")
