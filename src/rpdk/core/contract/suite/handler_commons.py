# have to skip B404, import_subprocess is required for executing typescript
# have to skip B60*, to allow typescript code to be executed using subprocess
import logging
import subprocess  # nosec
import tempfile

from rpdk.core.contract.interface import Action, HandlerErrorCode, OperationStatus
from rpdk.core.contract.resource_client import (
    prune_properties_from_model,
    prune_properties_if_not_exist_in_path,
)
from rpdk.core.contract.suite.contract_asserts import (
    failed_event,
    response_contains_primary_identifier,
    response_contains_resource_model_equal_updated_model,
    response_contains_unchanged_primary_identifier,
    response_does_not_contain_write_only_properties,
)
from rpdk.core.jsonutils.utils import traverse

LOG = logging.getLogger(__name__)


@response_contains_primary_identifier
@response_does_not_contain_write_only_properties
def test_create_success(resource_client, current_resource_model):
    _status, response, _error_code = resource_client.call_and_assert(
        Action.CREATE, OperationStatus.SUCCESS, current_resource_model
    )
    return response


@failed_event(
    error_code=HandlerErrorCode.AlreadyExists,
    msg="A create handler MUST NOT create multiple resources given\
         the same idempotency token",
)
def test_create_failure_if_repeat_writeable_id(resource_client, current_resource_model):
    LOG.debug(
        "at least one identifier is writeable; "
        "performing duplicate-CREATE-failed test"
    )
    # Should fail, because different clientRequestToken for the same
    # resource model means that the same resource is trying to be
    # created twice.
    _status, _response, error_code = resource_client.call_and_assert(
        Action.CREATE, OperationStatus.FAILED, current_resource_model
    )
    return error_code


@response_contains_primary_identifier
@response_does_not_contain_write_only_properties
def test_read_success(resource_client, current_resource_model):
    _status, response, _error_code = resource_client.call_and_assert(
        Action.READ, OperationStatus.SUCCESS, current_resource_model
    )
    test_input_equals_output(
        resource_client, current_resource_model, response["resourceModel"]
    )
    return response


@failed_event(
    error_code=HandlerErrorCode.NotFound,
    msg="A read handler MUST return FAILED with a NotFound error code\
         if the resource does not exist",
)
def test_read_failure_not_found(
    resource_client,
    current_resource_model,
):
    _status, _response, error_code = resource_client.call_and_assert(
        Action.READ, OperationStatus.FAILED, current_resource_model
    )
    return error_code


def get_resource_model_list(resource_client, current_resource_model):
    _status, response, _error_code = resource_client.call_and_assert(
        Action.LIST, OperationStatus.SUCCESS, current_resource_model
    )
    next_token = response.get("nextToken")
    resource_models = response["resourceModels"]
    while next_token is not None:
        _status, next_response, _error_code = resource_client.call_and_assert(
            Action.LIST,
            OperationStatus.SUCCESS,
            current_resource_model,
            nextToken=next_token,
        )
        resource_models.extend(next_response["resourceModels"])
        next_token = next_response.get("nextToken")
    return resource_models


def test_model_in_list(resource_client, current_resource_model):
    resource_models = get_resource_model_list(resource_client, current_resource_model)
    return any(
        resource_client.is_primary_identifier_equal(
            resource_client.primary_identifier_paths,
            resource_model,
            current_resource_model,
        )
        for resource_model in resource_models
    )


@response_contains_primary_identifier
@response_contains_unchanged_primary_identifier
@response_contains_resource_model_equal_updated_model
@response_does_not_contain_write_only_properties
def test_update_success(resource_client, update_resource_model, current_resource_model):
    _status, response, _error_code = resource_client.call_and_assert(
        Action.UPDATE,
        OperationStatus.SUCCESS,
        update_resource_model,
        current_resource_model,
    )
    return response


@failed_event(
    error_code=HandlerErrorCode.NotFound,
    msg="An update handler MUST return FAILED with a NotFound error code\
         if the resource did not exist prior to the update request",
)
def test_update_failure_not_found(resource_client, current_resource_model):
    update_model = resource_client.generate_update_example(current_resource_model)
    _status, _response, error_code = resource_client.call_and_assert(
        Action.UPDATE, OperationStatus.FAILED, update_model, current_resource_model
    )
    return error_code


def test_delete_success(resource_client, current_resource_model):
    _status, response, _error_code = resource_client.call_and_assert(
        Action.DELETE, OperationStatus.SUCCESS, current_resource_model
    )
    return response


@failed_event(
    error_code=HandlerErrorCode.NotFound,
    msg="A delete hander MUST return FAILED with a NotFound error code\
         if the resource did not exist prior to the delete request",
)
def test_delete_failure_not_found(resource_client, current_resource_model):
    _status, _response, error_code = resource_client.call_and_assert(
        Action.DELETE, OperationStatus.FAILED, current_resource_model
    )
    return error_code


def test_input_equals_output(resource_client, input_model, output_model):
    pruned_input_model = prune_properties_from_model(
        input_model.copy(), resource_client.write_only_paths
    )

    pruned_output_model = prune_properties_if_not_exist_in_path(
        output_model.copy(), pruned_input_model, resource_client.read_only_paths
    )

    pruned_output_model = prune_properties_if_not_exist_in_path(
        pruned_output_model, pruned_input_model, resource_client.create_only_paths
    )

    assertion_error_message = (
        "All properties specified in the request MUST "
        "be present in the model returned, and they MUST"
        " match exactly, with the exception of properties"
        " defined as writeOnlyProperties in the resource schema"
    )
    # only comparing properties in input model to those in output model and
    # ignoring extraneous properties that maybe present in output model.
    try:
        transform_model1(pruned_input_model, pruned_output_model, resource_client)
        for key in pruned_input_model:
            if key in resource_client.properties_without_insertion_order:
                assert test_unordered_list_match(
                    pruned_input_model[key], pruned_output_model[key]
                )
            else:
                assert (
                    pruned_input_model[key] == pruned_output_model[key]
                ), assertion_error_message
    except KeyError as e:
        raise AssertionError(assertion_error_message) from e


def test_unordered_list_match(inputs, outputs):
    assert len(inputs) == len(outputs)
    try:
        assert all(input in outputs for input in inputs)
    except KeyError as exception:
        raise AssertionError("lists do not match") from exception


def transform_model1(input_model, output_model, resource_client):
    if not resource_client.property_transform_keys:
        check_npm()
    for prop in resource_client.property_transform_keys:
        document_input, _path_input, _parent_input = traverse(
            input_model, list(prop)[1:]
        )
        document_output, _path_output, _parent_output = traverse(
            output_model, list(prop)[1:]
        )
        if document_input != document_output:
            transformed_property = transform(prop, input_model, resource_client)
            update_transformed_property(prop, transformed_property, input_model)


def transform(property_path, input_model, resource_client):

    path = "/" + "/".join(property_path)
    property_transform_value = resource_client.property_transform[path].replace(
        '"', '\\"'
    )

    content = resource_client.transformation_template.render(
        input_model=input_model, jsonata_expression=property_transform_value
    )

    file = tempfile.NamedTemporaryFile(
        mode="w+b",
        buffering=-1,
        encoding=None,
        newline=None,
        suffix=".js",
        prefix=None,
        dir=".",
        delete=True,
    )
    file.write(str.encode(content))

    LOG.debug("Jsonata transformation content %s", file.read().decode())
    jsonata_output = subprocess.getoutput("node " + file.name)

    file.close()
    return jsonata_output


def check_npm():
    output = subprocess.getoutput("npm list jsonata")
    if "npm: command not found" not in output:
        if "jsonata@" not in output:
            subprocess.getoutput("npm install jsonata")
    else:
        LOG.error(
            "NPM is required to support propertyTransform. "
            "Please install npm using the following link: https://www.npmjs.com/get-npm"
        )


def update_transformed_property(property_path, transformed_property, input_model):
    try:
        _prop, resolved_path, parent = traverse(input_model, list(property_path)[1:])
    except LookupError:
        LOG.debug("Override failed.\nPath %s\nDocument %s", property_path, input_model)
        LOG.warning("Override with path %s not found, skipping", property_path)
    else:
        key = resolved_path[-1]
        parent[key] = transformed_property
