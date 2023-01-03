# pylint: disable=import-outside-toplevel
import logging

import pytest

from rpdk.core.contract.hook_client import HookClient
from rpdk.core.contract.interface import HandlerErrorCode, HookStatus
from rpdk.core.contract.suite.contract_asserts_commons import failed_event

LOG = logging.getLogger(__name__)

TARGET_NAME_REGEX = "^[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}$"

UNSUPPORTED_TARGET_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "arn"},
        "property1": {"type": "string", "pattern": "^[a-zA-Z0-9]{2,26}$"},
        "property2": {"type": "integer", "minimum": 1, "maximum": 100},
    },
}


def test_hook_success(hook_client, invocation_point, target, target_model):
    if HookClient.is_update_invocation_point(invocation_point):
        raise ValueError(
            "Invocation point {} not supported for this testing operation".format(
                invocation_point
            )
        )

    _status, response, _error_code = hook_client.call_and_assert(
        invocation_point, HookStatus.SUCCESS, target, target_model
    )

    return response


def test_update_hook_success(hook_client, invocation_point, target, target_model):
    if not HookClient.is_update_invocation_point(invocation_point):
        raise ValueError(
            "Invocation point {} not supported for testing UPDATE hook operation".format(
                invocation_point
            )
        )

    _status, response, _error_code = hook_client.call_and_assert(
        invocation_point, HookStatus.SUCCESS, target, target_model
    )

    return response


def test_hook_failed(hook_client, invocation_point, target, target_model=None):
    _status, response, error_code = hook_client.call_and_assert(
        invocation_point, HookStatus.FAILED, target, target_model
    )
    assert response["message"]
    return response, error_code


def test_hook_handlers_success(hook_client, invocation_point):
    is_update_hook = HookClient.is_update_invocation_point(invocation_point)
    for (
        _invocation_point,
        target,
        target_model,
    ) in hook_client.generate_request_examples(invocation_point):
        if is_update_hook:
            test_update_hook_success(
                hook_client, invocation_point, target, target_model
            )
        else:
            test_hook_success(hook_client, invocation_point, target, target_model)


def test_hook_handlers_failed(hook_client, invocation_point):
    for (
        _invocation_point,
        target,
        target_model,
    ) in hook_client.generate_invalid_request_examples(invocation_point):
        test_hook_failed(hook_client, invocation_point, target, target_model)


@failed_event(
    error_code=HandlerErrorCode.UnsupportedTarget,
    msg="A hook handler MUST return FAILED with a UnsupportedTarget error code if the target is not supported",
)
def test_hook_unsupported_target(hook_client, invocation_point):
    if not hook_client.handler_has_wildcard_targets(invocation_point):
        pytest.skip("No wildcard hook targets. Skipping test.")

    # imported here to avoid hypothesis being loaded before pytest is loaded
    from ...resource_generator import ResourceGenerator

    unsupported_target = ResourceGenerator(
        UNSUPPORTED_TARGET_SCHEMA
    ).generate_schema_strategy(UNSUPPORTED_TARGET_SCHEMA)

    target_model = {"resourceProperties": unsupported_target.example()}
    if HookClient.is_update_invocation_point(invocation_point):
        target_model["previousResourceProperties"] = unsupported_target.example()
        target_model["previousResourceProperties"]["id"] = target_model[
            "resourceProperties"
        ]["id"]

    _response, error_code = test_hook_failed(
        hook_client,
        invocation_point,
        ResourceGenerator.generate_string_strategy(
            {"pattern": TARGET_NAME_REGEX}
        ).example(),
        target_model,
    )

    return error_code
