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
    _exercise_creation_tests_and_cleanup(resource_client, request, create_model)

    _setup_deletion_tests_and_exercise(resource_client)

    request = create_request

    input_for_cleanup = request
    try:
        # CREATE the same resource after DELETE
        input_for_cleanup = _request_from_result(
            resource_client,
            _invoke_resource_action(resource_client, Action.CREATE, request),
        )
    finally:
        # DELETE
        _invoke_resource_action(resource_client, Action.DELETE, input_for_cleanup)


def _exercise_creation_tests_and_cleanup(resource_client, request, create_model):
    input_for_cleanup = request
    try:
        # CREATE
        input_for_cleanup = _request_from_result(
            resource_client,
            _invoke_resource_action(resource_client, Action.CREATE, request),
        )

        # CREATE (idempotent, because same clientRequestToken)
        input_for_cleanup = _request_from_result(
            resource_client,
            _invoke_resource_action(resource_client, Action.CREATE, request),
        )

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
        _invoke_resource_action(resource_client, Action.DELETE, input_for_cleanup)


def _setup_deletion_tests_and_exercise(resource_client):
    create_model = resource_client.generate_create_example()
    request = resource_client.make_request(
        create_model, None, clientRequestToken=resource_client.generate_token()
    )

    creation_response = _invoke_resource_action(resource_client, Action.CREATE, request)

    _invoke_resource_action(
        resource_client,
        Action.DELETE,
        _request_from_result(resource_client, creation_response),
    )


def _request_from_result(resource_client, result):
    return resource_client.make_request(
        result["resourceModel"],
        None,
        clientRequestToken=resource_client.generate_token(),
    )


def _invoke_resource_action(resource_client, action, request):
    status, response = resource_client.call(action, request)
    resource_client.assert_success(status, response)
    return response
