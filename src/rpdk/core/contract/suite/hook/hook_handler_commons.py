import logging

from rpdk.core.contract.hook_client import HookClient
from rpdk.core.contract.interface import HookStatus

LOG = logging.getLogger(__name__)


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
