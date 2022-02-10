import pytest

from rpdk.core.contract.interface import Action, HookInvocationPoint
from rpdk.core.utils.handler_utils import generate_handler_name

RESOURCE_HANDLERS = {
    Action.CREATE: "create",
    Action.UPDATE: "update",
    Action.DELETE: "delete",
    Action.READ: "read",
    Action.LIST: "list",
}

HOOK_HANDLERS = {
    HookInvocationPoint.CREATE_PRE_PROVISION: "preCreate",
    HookInvocationPoint.UPDATE_PRE_PROVISION: "preUpdate",
    HookInvocationPoint.DELETE_PRE_PROVISION: "preDelete",
}


def test_generate_handler_name():
    operation = "SOME_HANDLER_OPERATION"
    expected_handler_name = "someHandlerOperation"

    handler_name = generate_handler_name(operation)
    assert handler_name == expected_handler_name


@pytest.mark.parametrize(
    "action", [Action.CREATE, Action.UPDATE, Action.DELETE, Action.READ, Action.LIST]
)
def test_generate_resource_handler_name(action):
    assert generate_handler_name(action) == RESOURCE_HANDLERS[action]


@pytest.mark.parametrize(
    "invoke_point",
    [
        HookInvocationPoint.CREATE_PRE_PROVISION,
        HookInvocationPoint.UPDATE_PRE_PROVISION,
        HookInvocationPoint.DELETE_PRE_PROVISION,
    ],
)
def test_generate_hook_handler_name(invoke_point):
    assert generate_handler_name(invoke_point) == HOOK_HANDLERS[invoke_point]
