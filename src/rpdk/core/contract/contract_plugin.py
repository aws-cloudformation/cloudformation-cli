import logging

import pytest

LOG = logging.getLogger(__name__)


class ContractPlugin:
    def __init__(self, *_args, **_kwargs):
        self._resource_client = None

    @pytest.fixture
    def resource_client(self):
        return self._resource_client
