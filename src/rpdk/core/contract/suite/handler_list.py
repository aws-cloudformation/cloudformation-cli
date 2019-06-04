def contract_list_empty(resource_client):
    list_response = resource_client.list_resources()
    assert list_response["status"] == resource_client.COMPLETE
    assert list_response["resources"] == []
