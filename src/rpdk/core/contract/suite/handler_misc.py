import logging

import pytest

# WARNING: contract tests should use fully qualified imports to avoid issues
# when being loaded by pytest
from rpdk.core.contract.interface import Action, HandlerErrorCode

LOG = logging.getLogger(__name__)


def contract_check_asserts_work():
    message = (
        "Asserts have been stripped. This is unusual, but happens if the "
        "contract tests are compiled to optimized byte code. As a result, the "
        "contract tests will not run correctly. Please raise an issue with "
        "as much information about your system and runtime as possible."
    )
    with pytest.raises(AssertionError):
        assert False  # noqa: B011
        pytest.fail(message)


def contract_crud_exerciser(resource_client):
    create_model = resource_client.generate_create_example()
    request = create_request = resource_client.make_request(
        create_model, None, clientRequestToken=resource_client.generate_token()
    )

    input_for_cleanup = request

    try:
        # CREATE
        status, response = resource_client.call(Action.CREATE, request)
        resource_client.assert_success(status, response)
        input_for_cleanup = _request_from_result(resource_client, response)

        # CREATE (idempotent, because same clientRequestToken)
        status, response = resource_client.call(Action.CREATE, request)
        resource_client.assert_success(status, response)

        # if no identifiers are writeable, then multiple requests with the same
        # model can succeed
        if resource_client.has_writable_identifier():
            LOG.debug(
                "at least one identifier is writeable; "
                "performing duplicate-CREATE-failed test"
            )
            # CREATE (not idempotent, because different clientRequestToken)
            second_request = resource_client.make_request(create_model, None)
            status, response = resource_client.call(Action.CREATE, second_request)
            error_code = resource_client.assert_failed(status, response)
            assert (
                error_code == HandlerErrorCode.AlreadyExists
            ), "creating the same resource should not be possible"
        else:
            LOG.debug(
                "no identifiers are writeable; " "skipping duplicate-CREATE-failed test"
            )

    finally:
        # DELETE
        status, response = resource_client.call(Action.DELETE, input_for_cleanup)
        resource_client.assert_success(status, response)

    # DELETE
    status, response = resource_client.call(Action.DELETE, input_for_cleanup)
    error_code = resource_client.assert_failed(status, response)
    assert error_code == HandlerErrorCode.NotFound

    request = create_request
    input_for_cleanup = request
    try:
        # CREATE the same resource after DELETE
        status, response = resource_client.call(Action.CREATE, request)
        resource_client.assert_success(status, response)
        input_for_cleanup = _request_from_result(resource_client, response)
    finally:
        # DELETE
        status, response = resource_client.call(Action.DELETE, input_for_cleanup)
        resource_client.assert_success(status, response)


def _request_from_result(resource_client, result):
    return resource_client.make_request(result["resourceModel"], None)
