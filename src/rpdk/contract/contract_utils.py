import time
from uuid import uuid4

import pytest

from ..jsonutils.pointer import fragment_decode

CREATE = "CREATE"
READ = "READ"
UPDATE = "UPDATE"
DELETE = "DELETE"
LIST = "LIST"
ALREADY_EXISTS = "AlreadyExists"
NOT_UPDATABLE = "NotUpdatable"
NOT_FOUND = "NotFound"
NO_OP = "NoOperationToPerform"
IN_PROGRESS = "IN_PROGRESS"
COMPLETE = "COMPLETE"
FAILED = "FAILED"
ACK_TIMEOUT = 3


def get_identifier_property(resource_def, resource_model):
    id_reference = fragment_decode(resource_def["identifiers"][0])
    return id_reference[-1], resource_model["properties"][id_reference[-1]]


def wait_for_specified_event(listener, specified_event, timeout_in_seconds=60):
    events = []
    start_time = time.time()
    specified = False
    while ((time.time() - start_time) < timeout_in_seconds) and not specified:
        time.sleep(0.5)
        while listener.events:
            event = listener.events.popleft()
            events.append(event)
            if event.get("status", "") in (specified_event, FAILED):
                specified = True
    return events


def prepare_request(
    operation, resource_type, token=None, resource=None, previous_resource=None
):
    if not token:
        token = str(uuid4())
    request = {
        "requestContext": {
            "resourceType": resource_type,
            "operation": operation,
            "clientRequestToken": token,
        },
        "requestData": {},
    }
    if resource:
        request["requestData"]["resourceProperties"] = resource["properties"]
    if previous_resource:
        request["requestData"]["previousResourceProperties"] = previous_resource[
            "properties"
        ]
    return request, token


def verify_events_contain_token(events, token):
    if any(event["clientRequestToken"] != token for event in events):
        raise AssertionError(
            "Request tokens:\n"
            + "\n".join(event["clientRequestToken"] for event in events)
        )


def create_resource(event_listener, transport, resource):
    request, token = prepare_request(CREATE, resource["type"], resource=resource)
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, COMPLETE)
    verify_events_contain_token(events, token)
    return events[-1]


def read_resource(event_listener, transport, resource, resource_def):
    id_key, id_value = get_identifier_property(resource_def, resource)
    id_resource = {"type": resource["type"]}
    id_resource["properties"] = {id_key: id_value}
    request, token = prepare_request(
        READ, resource_def["typeName"], resource=id_resource
    )
    read_response = transport(request, event_listener.server_address)
    assert read_response["clientRequestToken"] == token  # nosec
    return read_response


def update_resource(event_listener, transport, resource, updated_resource):
    request, token = prepare_request(
        UPDATE, resource["type"], resource=updated_resource, previous_resource=resource
    )
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, COMPLETE)
    verify_events_contain_token(events, token)
    return events[-1]


def delete_resource(event_listener, transport, resource, resource_def):
    id_key, id_value = get_identifier_property(resource_def, resource)
    request, token = prepare_request(
        DELETE, resource["type"], resource={"properties": {id_key: id_value}}
    )
    transport(request, event_listener.server_address)
    events = wait_for_specified_event(event_listener, COMPLETE)
    verify_events_contain_token(events, token)
    return events[-1]


def compare_requested_model(requested_model, returned_model, resource_def):
    # Do not need to check write only properties in requested model.
    write_only_properties = {
        fragment_decode(prop)[-1] for prop in resource_def.get("writeOnly", ())
    }
    comparable_properties = (
        set(requested_model["properties"].keys()) - write_only_properties
    )
    for key in comparable_properties:
        assert (  # nosec
            returned_model["properties"][key] == requested_model["properties"][key]
        )


def check_for_writable_identifiers(test_resource, resource_def):
    # Need to have non readOnly identifiers for this test to be worthwhile,
    # because otherwise tests involving creates after deletes/creates
    # with the same properties is simply creating another resource
    encoded_writable_identifiers = set(resource_def["identifiers"]) - set(
        resource_def["readOnly"]
    )
    writable_identifiers = {
        fragment_decode(identifier)[-1] for identifier in encoded_writable_identifiers
    }
    if not set(test_resource["properties"].keys() & writable_identifiers):
        pytest.skip("No writable identifiers")
