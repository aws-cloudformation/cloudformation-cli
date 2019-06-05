import logging
import threading
from collections import deque
from uuid import uuid4

from werkzeug.serving import make_server
from werkzeug.wrappers import Request, Response

from ..exceptions import InvalidRequestError

LOG = logging.getLogger(__name__)

RECORD_ACTION = "RecordHandlerProgress"


class CallbackServer(threading.Thread):
    def __init__(self, host="127.0.0.1", port=0):
        self.events = deque()
        self._server = make_server(host, port, self, ssl_context=None)
        self.server_address = self._server.server_address
        super().__init__(name=self.__class__, target=self._server.serve_forever)

    @property
    def endpoint_url(self):
        return "http://{}:{}".format(*self.server_address)

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

    def _error_response(self, message):
        self.events.append(InvalidRequestError(message))
        request_id = uuid4()
        return Response(
            """<ErrorResponse
    xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
  <Error>
    <Type>Sender</Type>
    <Code>ValidationError</Code>
    <Message>{}</Message>
  </Error>
  <RequestId>{}</RequestId>
</ErrorResponse>""".format(
                message, request_id
            ),
            mimetype="text/xml",
            status=400,
            headers={"x-amzn-RequestId": request_id, "Connection": "close"},
        )

    @staticmethod
    def _success_response():
        request_id = uuid4()
        return Response(
            """<RecordHandlerProgressResponse
    xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
  <RecordHandlerProgressResult/>
  <ResponseMetadata>
    <RequestId>{}</RequestId>
  </ResponseMetadata>
</RecordHandlerProgressResponse>""".format(
                request_id
            ),
            mimetype="text/xml",
            status=200,
            headers={"x-amzn-RequestId": request_id},
        )

    @Request.application
    def __call__(self, request):
        # this should never happen when using the AWS SDK
        assert request.method == "POST"

        action = request.form.get("Action")
        if action != RECORD_ACTION:
            message = "Invalid action (expected '{}')".format(RECORD_ACTION)
            return self._error_response(message)

        token = request.form.get("BearerToken")
        if token.startswith("invalid"):
            # the error response was sniffed from the real service and
            # should match exactly
            return self._error_response("The specified BearerToken does not exist")

        # we could do more validation here, but the AWS SDKs should do most of the work

        self.events.append(
            {
                k: v
                for k, v in request.form.items()
                if k
                in {
                    "BearerToken",
                    "OperationStatus",
                    "StatusMessage",
                    "ErrorCode",
                    "ResourceModel",
                }
            }
        )
        return self._success_response()
