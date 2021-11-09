import logging

from rpdk.core.contract.hook_client import HookClient
from rpdk.core.contract.interface import HandlerErrorCode, HookStatus
from rpdk.core.contract.suite.contract_asserts_commons import failed_event

LOG = logging.getLogger(__name__)

UNSUPPORTED_TARGET = "AWS::FakeService::Resource"


def _prepare_target_model(invocation_point):
    target_model = {"resourceProperties": {}}
    if HookClient.is_update_invocation_point(invocation_point):
        target_model["previousResourceProperties"] = {}

    return target_model


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


@failed_event(
    error_code=HandlerErrorCode.InvalidRequest,
    msg="A hook handler MUST return FAILED with a InvalidRequest error code if the target is not supported",
)
def test_hook_unsupported_target(hook_client, invocation_point):
    target_model = _prepare_target_model(invocation_point)

    _response, error_code = test_hook_failed(
        hook_client,
        invocation_point,
        UNSUPPORTED_TARGET,
        target_model,
    )

    return error_code


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
