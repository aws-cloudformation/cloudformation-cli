import json

import boto3
from botocore import UNSIGNED
from botocore.config import Config


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
        _, port = callback_endpoint
        url = "http://host.docker.internal:{}".format(port)
        payload["requestContext"]["callbackURL"] = url
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        response = self.client.invoke(FunctionName=self.function_name, Payload=encoded)
        return json.load(response["Payload"])
