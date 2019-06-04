import json
import logging
import threading
from collections import deque

from werkzeug.serving import make_server
from werkzeug.wrappers import Request, Response

LOG = logging.getLogger(__name__)

JSON_MIME = "application/json"


class CallbackServer(threading.Thread):
    def __init__(self, host="127.0.0.1", port=0):
        self.events = deque()
        self._server = make_server(host, port, self, ssl_context=None)
        self.server_address = self._server.server_address
        super().__init__(name=self.__class__, target=self._server.serve_forever)

    def __enter__(self):
        self.start()
        LOG.debug(
            "Started callback server at address %s on port %s", *self.server_address
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __del__(self):  # pragma: no cover
        # don't cover finalizers in tests, you'd have to force garbage collection.
        # this is a fallback in case somebody forgets to use a with statement.
        self.stop()

    def stop(self):
        self._server.shutdown()

    @Request.application
    def __call__(self, request):
        content_type = request.headers.get("content-type")
        if content_type != JSON_MIME:
            err_msg = "callback with invalid content type '{}'".format(content_type)
            LOG.error(err_msg)
            event = {"error": err_msg}
        else:
            LOG.debug("Received event %s", request.data)
            event = json.loads(request.data)
        self.events.append(event)
        return Response("", mimetype=JSON_MIME)
