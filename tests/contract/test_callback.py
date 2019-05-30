# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import json

import boto3
import pytest
from botocore.exceptions import ClientError

from rpdk.core.contract.callback import CallbackServer
from rpdk.core.exceptions import InvalidRequestError


def test_callback_server_other_api():
    with CallbackServer() as listener:
        client = boto3.client("cloudformation", endpoint_url=listener.endpoint_url)

        with pytest.raises(ClientError) as excinfo:
            client.list_stacks()

    assert "ListStacks" in str(excinfo.value)
    assert "RecordHandlerProgress" in str(excinfo.value)
    assert len(listener.events) == 1
    event = listener.events.popleft()
    assert isinstance(event, InvalidRequestError)


def test_callback_server_invalid_token():
    with CallbackServer() as listener:
        client = boto3.client("cloudformation", endpoint_url=listener.endpoint_url)

        with pytest.raises(ClientError) as excinfo:
            client.record_handler_progress(
                BearerToken="invalidx-8259-11e9-8b6b-25f97fa64ab5",
                OperationStatus="SUCCESS",
            )

    assert "BearerToken" in str(excinfo.value)
    assert len(listener.events) == 1
    event = listener.events.popleft()
    assert isinstance(event, InvalidRequestError)


def test_callback_server_valid_token():
    progress = {
        "BearerToken": "bca152a7-8259-11e9-8b6b-25f97fa64ab5",
        "OperationStatus": "FAILED",
        "ErrorCode": "NotReady",
        "StatusMessage": "Impending doom",
        "ResourceModel": json.dumps({"Planet": "Alderaan"}),
    }
    with CallbackServer() as listener:
        client = boto3.client("cloudformation", endpoint_url=listener.endpoint_url)
        client.record_handler_progress(**progress)

    assert len(listener.events) == 1
    event = listener.events.popleft()
    assert event == progress
