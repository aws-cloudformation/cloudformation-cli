import logging

import pytest

from rpdk.core.contract.interface import HookInvocationPoint
from rpdk.core.contract.suite.hook.hook_handler_commons import (
    test_hook_handlers_failed,
    test_hook_handlers_success,
)

LOG = logging.getLogger(__name__)

INVOCATION_POINT = HookInvocationPoint.UPDATE_PRE_PROVISION


@pytest.mark.update_pre_provision
def contract_pre_update_success(hook_client):
    test_hook_handlers_success(hook_client, INVOCATION_POINT)


@pytest.mark.update_pre_provision
def contract_pre_update_failed(hook_client):
    test_hook_handlers_failed(hook_client, INVOCATION_POINT)
