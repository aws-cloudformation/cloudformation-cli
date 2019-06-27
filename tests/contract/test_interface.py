# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import json

import boto3
import pytest

from rpdk.core.contract.interface import Action, HandlerErrorCode, OperationStatus


@pytest.fixture
def client():
    return boto3.client(
        "cloudformation",
        aws_access_key_id="",
        aws_secret_access_key="",
        aws_session_token="",
    )


def test_operation_status_enum_matches_sdk(client):
    sdk = set(client.meta.service_model.shape_for("OperationStatus").enum)
    enum = set(OperationStatus.__members__)
    assert enum == sdk


def test_handler_error_code_enum_matches_sdk(client):
    sdk = set(client.meta.service_model.shape_for("HandlerErrorCode").enum)
    enum = set(HandlerErrorCode.__members__)
    assert enum == sdk


def test_action_enum_is_json_serializable():
    json.dumps({"action": Action.CREATE})
