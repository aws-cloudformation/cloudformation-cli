from rpdk.core.contract.resource_client import ResourceClient


def test_generate_token():
    token = ResourceClient.generate_token()
    assert isinstance(token, str)
    assert len(token) == 36


def test_make_request():
    desired_resource_state = object()
    previous_resource_state = object()
    token = object()
    request = ResourceClient.make_request(
        desired_resource_state, previous_resource_state, clientRequestToken=token
    )
    assert request == {
        "desiredResourceState": desired_resource_state,
        "previousResourceState": previous_resource_state,
        "logicalResourceIdentifier": None,
        "clientRequestToken": token,
    }
