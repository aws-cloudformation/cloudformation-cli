from .. import contract_utils


def contract_list_empty(resource_client):
    list_response = resource_client.list_resources()
    assert list_response["status"] == contract_utils.COMPLETE
    assert list_response["resources"] == []
