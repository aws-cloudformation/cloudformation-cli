# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
# pylint: disable=protected-access
import pkg_resources
import pytest
import yaml

from rpdk.jsonutils.jsonschema_normalizer import (
    JsonSchemaNormalizer,
    NormalizationError,
)


@pytest.fixture
def test_provider_schema():
    resource = pkg_resources.resource_stream("tests", "schemas/area_definition.json")
    return yaml.safe_load(resource)


@pytest.fixture
def normalized_schema():
    resource = pkg_resources.resource_stream(
        "tests", "schemas/area_definition_normalized.json"
    )
    return yaml.safe_load(resource)


@pytest.fixture
def normalizer(test_provider_schema):
    return JsonSchemaNormalizer(test_provider_schema)


def test_normalizer(normalizer, normalized_schema):
    normalized_schema_map = normalizer.collapse_and_resolve_schema()

    assert normalized_schema == normalized_schema_map


def test_collapse_primitive_type(normalizer):
    items = [
        {"type": "string"},
        {"type": "integer"},
        {"type": "number"},
        {"type": "object"},
        {"type": "array"},
        {"type": "boolean"},
    ]
    for schema in items:
        assert schema == normalizer._collapse_and_resolve_subschema(
            "#/properties/Test", schema
        )


def test_ref_type_to_primitive(normalizer):
    schema_path = "#/properties/areaId"
    expected_schema = {"type": "string"}
    collapsed_schema = normalizer._collapse_ref_type(schema_path)

    assert expected_schema == collapsed_schema
    assert not normalizer._schema_map


def test_property_path_already_processed(normalizer):
    normalizer._schema_map = {"#/properties/City": {}}
    assert len(normalizer._schema_map) == 1
    result = normalizer._collapse_and_resolve_subschema(
        "#/properties/City", {"type": "object", "properties": {"test": {}}}
    )
    assert result == {"$ref": "#/properties/City"}
    assert len(normalizer._schema_map) == 1


def test_collapse_ref_type(normalizer, normalized_schema):
    schema_path = "#/definitions/boundary/properties/box/properties/north"
    expected_collapsed_schema = {"$ref": "#/definitions/coordinate"}
    coordinate_path = "#/definitions/coordinate"

    collapsed_schema = normalizer._collapse_ref_type(schema_path)

    assert expected_collapsed_schema == collapsed_schema
    assert normalizer._schema_map[coordinate_path] == normalized_schema[coordinate_path]
    assert len(normalizer._schema_map) == 1


def test_collapse_ref_type_nested(normalizer, normalized_schema):
    schema_path = "#/definitions/boundary/properties/box"
    expected_collapsed_schema = {"$ref": "#/definitions/boundary/properties/box"}
    coordinate_path = "#/definitions/coordinate"

    collapsed_schema = normalizer._collapse_ref_type(schema_path)

    assert expected_collapsed_schema == collapsed_schema
    assert normalizer._schema_map[schema_path] == normalized_schema[schema_path]
    assert (
        normalizer._schema_map[coordinate_path]
        == normalized_schema["#/definitions/coordinate"]
    )
    assert len(normalizer._schema_map) == 2


def test_circular_reference():
    resource = pkg_resources.resource_stream(
        "tests", "schemas/circular_reference_normalized.json"
    )
    schema_normalized = yaml.safe_load(resource)

    resource = pkg_resources.resource_stream("tests", "schemas/circular_reference.json")
    schema = yaml.safe_load(resource)
    resolved_schema = JsonSchemaNormalizer(schema).collapse_and_resolve_schema()
    assert resolved_schema == schema_normalized


def test_collapse_array_type(normalizer, normalized_schema):
    property_key = "#/properties/city/properties/neighborhoods"
    unresolved_schema = normalizer._find_subschema_by_ref(property_key)
    resolved_schema = normalizer._collapse_array_type(property_key, unresolved_schema)
    new_key = "#/properties/city/properties/neighborhoods/items/patternProperties/%5BA-Za-z0-9%5D%7B1%2C64%7D"  # noqa: B950 pylint:disable=line-too-long
    expected_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "patternProperties": {"[A-Za-z0-9]{1,64}": {"$ref": new_key}},
            "insertionOrder": True,
        },
    }
    assert resolved_schema == expected_schema
    assert normalizer._schema_map[new_key] == normalized_schema[new_key]
    assert len(normalizer._schema_map) == 1


def test_find_schema_from_ref(normalizer, test_provider_schema):
    location_schema_expected = {
        "type": "object",
        "properties": {
            "country": {"type": "string"},
            "boundary": {"$ref": "#/definitions/boundary"},
        },
    }
    location_schema = normalizer._find_subschema_by_ref("#/definitions/location")
    assert location_schema == location_schema_expected

    expected_street_schema = {"type": "string"}
    street_schema = normalizer._find_subschema_by_ref(
        "#/properties/city/properties/neighborhoods/items/patternProperties/%5BA-Za-z0-9%5D%7B1%2C64%7D/properties/street"  # noqa: B950 pylint:disable=line-too-long
    )
    assert street_schema == expected_street_schema

    assert normalizer._find_subschema_by_ref("#") == test_provider_schema

    with pytest.raises(NormalizationError) as e:
        normalizer._find_subschema_by_ref("#/this/is/not/a/path")
        assert str(e) == "Invalid ref: #/this/is/not/a/path"
