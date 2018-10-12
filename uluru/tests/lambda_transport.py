import json

import boto3
from botocore import UNSIGNED
from botocore.config import Config

from .transport import Transport


class LocalLambdaTransport(Transport):
    def __init__(self, function_name, endpoint="http://127.0.0.1:3001"):
        self.client = boto3.client(
            "lambda",
            endpoint_url=endpoint,
            use_ssl=False,
            verify=False,
            config=Config(
                signature_version=UNSIGNED,
                read_timeout=5,
                retries={"max_attempts": 0},
                region_name="us-east-1",
            ),
        )
        self.function_name = function_name

    def send(self, payload, callback_endpoint):
        _, port = callback_endpoint
        url = "http://host.docker.internal:{}".format(port)
        payload["requestContext"]["callbackURL"] = url
        response = self.client.invoke(
            FunctionName=self.function_name, Payload=json.dumps(payload).encode("utf-8")
        )
        return response
