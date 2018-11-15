from .. import contract_utils


def contract_list_empty(event_listener, transport, resource_def):
    request, token = contract_utils.prepare_request(
        contract_utils.LIST, resource_def["typeName"]
    )
    list_response = transport(request, event_listener.server_address)

    assert list_response["clientRequestToken"] == token
    assert list_response["status"] == contract_utils.COMPLETE
    assert list_response["resources"] == []
