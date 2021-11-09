import pytest

from rpdk.core.contract.suite.contract_asserts_commons import decorate


@decorate()
def response_does_not_contain_write_only_properties(resource_client, response):
    resource_client.assert_write_only_property_does_not_exist(response["resourceModel"])


@decorate()
def response_contains_resource_model_equal_updated_model(
    response, current_resource_model, update_resource_model
):
    assert response["resourceModel"] == {
        **current_resource_model,
        **update_resource_model,
    }, "All properties specified in the update request MUST be present in the \
        model returned, and they MUST match exactly, with the exception of \
            properties defined as writeOnlyProperties in the resource schema"


@decorate()
def response_contains_primary_identifier(resource_client, response):
    resource_client.assert_primary_identifier(
        resource_client.primary_identifier_paths, response["resourceModel"]
    )


@decorate()
def response_contains_unchanged_primary_identifier(
    resource_client, response, current_resource_model
):
    assert resource_client.is_primary_identifier_equal(
        resource_client.primary_identifier_paths,
        current_resource_model,
        response["resourceModel"],
    ), "PrimaryIdentifier returned in every progress event must match \
        the primaryIdentifier passed into the request"


@decorate(after=False)
def skip_not_writable_identifier(resource_client):
    if not resource_client.has_only_writable_identifiers():
        pytest.skip("No writable identifiers. Skipping test.")


@decorate(after=False)
def skip_no_tagging(resource_client):
    if not resource_client.contains_tagging_metadata():
        pytest.skip("Resource does not contain tagging metadata. Skipping test.")


@decorate(after=False)
def skip_not_taggable(resource_client):
    if not resource_client.is_taggable():
        pytest.skip("Resource is not taggable. Skipping test.")


@decorate(after=False)
def skip_not_tag_updatable(resource_client):
    if not resource_client.is_tag_updatable():
        pytest.skip("Resource is not tagUpdatable. Skipping test.")
