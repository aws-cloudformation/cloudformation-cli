import json

from botocore import UNSIGNED
from botocore.config import Config

from ..boto_helpers import create_sdk_session


class LocalLambdaTransport:
    def __init__(self, endpoint, function_name):
        self.endpoint = endpoint
        self.function_name = function_name
        self.client = create_sdk_session().client(
            "lambda",
            endpoint_url=self.endpoint,
            use_ssl=False,
            verify=False,
            config=Config(
                signature_version=UNSIGNED,
                read_timeout=10,
                retries={"max_attempts": 0},
                region_name="us-east-1",
            ),
        )

    def __call__(self, payload, callback_endpoint):
        """Sends the payload to the specified local lambda endpoint.
        If callback_endpoint is None, the operation
        is assumed to be synchronous,
        and the callback endpoint will not be set for the request."""
        try:
            _, port = callback_endpoint
        except TypeError:
            pass
        else:
            url = "http://host.docker.internal:{}".format(port)
            payload["requestContext"]["callbackURL"] = url
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        response = self.client.invoke(FunctionName=self.function_name, Payload=encoded)
        return json.load(response["Payload"])
