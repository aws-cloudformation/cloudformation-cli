import json

import boto3
from botocore import UNSIGNED
from botocore.config import Config


def transport(handler_type):
    if handler_type == "lambda":
        client = boto3.client(
            "lambda",
            endpoint_url="http://127.0.0.1:3001",
            use_ssl=False,
            verify=False,
            config=Config(
                signature_version=UNSIGNED,
                read_timeout=5,
                retries={"max_attempts": 0},
                region_name="us-east-1",
            ),
        )

        def call(request_payload):
            response = client.invoke(
                FunctionName="Handler", Payload=json.dumps(request_payload).encode()
            )
            return json.load(response["Payload"])

    return call


class HandlerClient:
    def __init__(self, handler_type):
        self.transport = transport(handler_type)

    def create(self, request_payload):
        request_payload["requestContext"]["operation"] = "Create"
        self.transport(request_payload)

    def read(self, request_payload):
        request_payload["requestContext"]["operation"] = "Read"
        return self.transport(request_payload)

    def update(self, request_payload):
        request_payload["requestContext"]["operation"] = "Update"
        self.transport(request_payload)

    def delete(self, request_payload):
        request_payload["requestContext"]["operation"] = "Delete"
        self.transport(request_payload)

    def list(self, request_payload):
        request_payload["requestContext"]["operation"] = "List"
        self.transport(request_payload)
