import logging

import pytest

from .contract_utils import COMPLETE, FAILED, NOT_FOUND, ResourceClient

JSON_MIME = "application/json"
LOG = logging.getLogger(__name__)


class ContractPlugin:
    def __init__(self, transport, test_resource, test_updated_resource, resource_def):
        self._test_resource = test_resource
        self._test_updated_resource = test_updated_resource
        self._resource_client = ResourceClient(transport, resource_def)

    @pytest.fixture
    def test_resource(self):
        return self._test_resource

    @pytest.fixture
    def test_updated_resource(self):
        return self._test_updated_resource

    @pytest.fixture
    def resource_client(self):
        return self._resource_client

    @pytest.fixture
    def created_resource(self):
        with ResourceFixture(self._resource_client, self._test_resource) as resource:
            yield resource


class ResourceFixture:
    def __init__(self, resource_client, resource):
        self._resource_client = resource_client
        try:
            create_terminal_event = self._resource_client.create_resource(resource)
            assert create_terminal_event["status"] == COMPLETE
            resource = create_terminal_event["resources"][0]
        except AssertionError as e:
            LOG.error("Could not create resource with given handler.")
            raise e
        self._resource = resource

    def __enter__(self):
        return self._resource

    def __exit__(self, exc_type, exc_val, exc_tb):
        delete_terminal_event = self._resource_client.delete_resource(self._resource)
        try:
            try:
                error_code = delete_terminal_event["errorCode"]
            except KeyError:
                assert delete_terminal_event["status"] == COMPLETE
            else:
                assert delete_terminal_event["status"] == FAILED
                assert error_code == NOT_FOUND
        except AssertionError as e:
            LOG.error("Could not delete resource with given handler")
            raise e
