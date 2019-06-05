import logging
from contextlib import contextmanager

import pytest

from .resource_client import ResourceClient

LOG = logging.getLogger(__name__)


class ContractPlugin:
    def __init__(self, resource_client, test_resource, test_updated_resource):
        self._test_resource = test_resource
        self._test_updated_resource = test_updated_resource
        self._resource_client = resource_client

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
        with self._created_resource() as resource:
            yield resource

    @contextmanager
    def _created_resource(self):
        try:
            create_terminal_event = self._resource_client.create_resource(
                self._test_resource
            )
            assert create_terminal_event["status"] == ResourceClient.COMPLETE
            resource = create_terminal_event["resources"][0]
        except Exception:
            LOG.exception("Could not create resource with given handler.")
            raise
        yield resource
        try:
            delete_terminal_event = self._resource_client.delete_resource(resource)
            try:
                error_code = delete_terminal_event["errorCode"]
            except KeyError:
                assert delete_terminal_event["status"] == ResourceClient.COMPLETE
            else:
                assert delete_terminal_event["status"] == ResourceClient.FAILED
                assert error_code == ResourceClient.NOT_FOUND
        except Exception:
            LOG.exception("Could not delete resource with given handler")
            raise
