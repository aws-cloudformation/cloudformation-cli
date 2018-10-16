import json

import boto3
from botocore import UNSIGNED
from botocore.config import Config

TRANSPORT_REGISTRY = {}


def register_transport(cls):
    """Registers a transport class in this module's registry
     to be used in handler contract testing.
        """
    TRANSPORT_REGISTRY[cls.__name__] = cls


@register_transport
class LocalLambdaTransport:
    def __init__(self, endpoint, function_name):
        self.endpoint = endpoint
        self.function_name = function_name
        self.client = boto3.client(
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
        __, port = callback_endpoint
        url = "http://host.docker.internal:{}".format(port)

        payload["requestContext"]["callbackURL"] = url
        response = self.client.invoke(
            FunctionName=self.function_name, Payload=json.dumps(payload).encode("utf-8")
        )
        return json.load(response["Payload"])
