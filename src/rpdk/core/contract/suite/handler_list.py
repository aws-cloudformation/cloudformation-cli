# fixture and parameter have the same name
# pylint: disable=redefined-outer-name

import pytest

# WARNING: contract tests should use fully qualified imports to avoid issues
# when being loaded by pytest
from rpdk.core.contract.interface import Action, OperationStatus


@pytest.mark.list
def contract_list_empty(resource_client):
    model = resource_client.generate_create_example()
    _status, response, _error_code = resource_client.call_and_assert(
        Action.LIST, OperationStatus.SUCCESS, model
    )
    if not response["resourceModels"]:
        assert True
    else:
        pytest.skip("Resources exist in the current account")
