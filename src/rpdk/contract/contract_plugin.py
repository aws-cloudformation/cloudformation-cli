import json
import threading
from collections import deque

import pytest
from werkzeug.serving import make_server
from werkzeug.wrappers import Request, Response

JSON_MIME = "application/json"


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
    def transport(self):
        return self._transport

    @pytest.fixture
    def resource_def(self):
        return self._resource_def

    @pytest.fixture
    def test_updated_resource(self):
        return self._test_updated_resource

    @staticmethod
    @pytest.fixture
    # this fixture can never be covered without raising a warning
    def event_listener(request):  # pragma: no cover
        return start_listener(request)


def start_listener(request):
    server = CallbackServer()
    server.start()
    request.addfinalizer(server.stop)
    return server


class CallbackServer(threading.Thread):
    def __init__(self, host="127.0.0.1", port=0):
        self.events = deque()
        self._server = make_server(host, port, self, ssl_context=None)
        self.server_address = self._server.server_address
        super().__init__(name=self.__class__, target=self._server.serve_forever)

    def __del__(self):
        self.stop()

    def stop(self):
        self._server.shutdown()

    @Request.application
    def __call__(self, request):
        response = ""
        content_type = request.headers.get("content-type")
        if content_type != JSON_MIME:
            json_response = {
                "error": 'callback with invalid content type "{}"'.format(content_type)
            }
            response = json.dumps(json_response)
        else:
            self.events.append(json.loads(request.data))
        return Response(response, mimetype=JSON_MIME)
