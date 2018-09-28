# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
# pylint: disable=protected-access
import pkg_resources
import pytest
import yaml

from uluru.json_schema_normalizer import JsonSchemaNormalizer


@pytest.fixture
def test_provider_schema():
    resource = pkg_resources.resource_stream(__name__, "schemas/area_definition.json")
    return yaml.safe_load(resource)


@pytest.fixture
def normalized_schema():
    from .schemas.area_definition_normalized import NORMALIZED_SCHEMA

    return NORMALIZED_SCHEMA


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
            "#/~properties/Test", schema
        )


def test_ref_type_to_primitive(normalizer):
    schema_path = "#/~properties/AreaId"
    expected_schema = {"type": "string"}
    collapsed_schema = normalizer._collapse_ref_type(schema_path)

    assert expected_schema == collapsed_schema
    assert not normalizer._schema_map.keys()


def test_collapse_ref_type(normalizer, normalized_schema):
    schema_path = "#/definitions/Boundary/~properties/Box/~properties/North"
    expected_collapsed_schema = {"$ref": "#/definitions/Coordinate"}
    coordinate_path = "#/definitions/Coordinate"

    collapsed_schema = normalizer._collapse_ref_type(schema_path)

    assert expected_collapsed_schema == collapsed_schema
    assert normalizer._schema_map[coordinate_path] == normalized_schema[coordinate_path]
    assert len(normalizer._schema_map.keys()) == 1


def test_collapse_ref_type_nested(normalizer, normalized_schema):
    schema_path = "#/definitions/Boundary/~properties/Box"
    expected_collapsed_schema = {"$ref": "#/definitions/Boundary/~properties/Box"}
    coordinate_path = "#/definitions/Coordinate"

    collapsed_schema = normalizer._collapse_ref_type(schema_path)

    assert expected_collapsed_schema == collapsed_schema
    assert normalizer._schema_map[schema_path] == normalized_schema[schema_path]
    assert (
        normalizer._schema_map[coordinate_path]
        == normalized_schema["#/definitions/Coordinate"]
    )
    assert len(normalizer._schema_map.keys()) == 2


def test_circular_reference():
    from .schemas.circular_reference_normalized import CIRCULAR_REFERENCE_SCHEMA

    resource = pkg_resources.resource_stream(
        __name__, "schemas/circular_reference.json"
    )
    schema = yaml.safe_load(resource)
    resolved_schema = JsonSchemaNormalizer(schema).collapse_and_resolve_schema()
    assert resolved_schema == CIRCULAR_REFERENCE_SCHEMA


def test_collapse_array_type(normalizer, normalized_schema):
    property_key = "#/~properties/City/~properties/Neighborhoods"
    unresolved_schema = normalizer._find_subschema_by_ref(property_key)
    resolved_schema = normalizer._collapse_array_type(property_key, unresolved_schema)
    new_key = (
        "#/~properties/City/~properties/Neighborhoods/~items/~additionalProperties"
    )
    expected_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": {"$ref": new_key},
            "insertionOrder": True,
        },
    }
    assert resolved_schema == expected_schema
    assert normalizer._schema_map[new_key] == normalized_schema[new_key]
    assert len(normalizer._schema_map.keys()) == 1


def test_find_schema_from_ref(normalizer, test_provider_schema):
    location_schema_expected = {
        "type": "object",
        "properties": {
            "Country": {"type": "string"},
            "Boundary": {"$ref": "#/definitions/Boundary"},
        },
    }
    location_schema = normalizer._find_subschema_by_ref("#/definitions/Location")
    assert location_schema == location_schema_expected

    expected_street_schema = {"type": "string"}
    street_schema = normalizer._find_subschema_by_ref(
        "#/~properties/City/~properties/Neighborhoods/~items/~additionalProperties/~properties/Street"  # noqa: B950 pylint:disable=line-too-long
    )
    assert street_schema == expected_street_schema

    assert normalizer._find_subschema_by_ref("#") == test_provider_schema
