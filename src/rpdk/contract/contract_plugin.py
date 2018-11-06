import json
from collections import deque

import pytest
from pytest_localserver.http import Request, Response, WSGIServer


class CallbackServer(WSGIServer):
    def __init__(self, host="127.0.0.1", port=0):
        super().__init__(host, port, self, ssl_context=None)
        self.events = deque()

    @Request.application
    def __call__(self, request):
        assert request.headers.get("content-type") == "application/json"  # nosec
        self.events.append(json.loads(request.data))
        return Response("", mimetype="application/json")


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

    @pytest.fixture
    def event_listener(self, request):  # pylint: disable=no-self-use
        server = CallbackServer()
        server.start()
        request.addfinalizer(server.stop)
        return server
