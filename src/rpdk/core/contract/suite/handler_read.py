# fixture and parameter have the same name
# pylint: disable=redefined-outer-name

import pytest

# WARNING: contract tests should use fully qualified imports to avoid issues
# when being loaded by pytest
from rpdk.core.contract.suite.handler_commons import test_read_failure_not_found


@pytest.mark.read
def contract_read_without_create(resource_client):
    model = (
        resource_client.generate_invalid_create_example()
    )  # to allow invalid (correctly formatted primary id)
    test_read_failure_not_found(resource_client, model)
