# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
# pylint: disable=protected-access
import string

import pytest

from rpdk.data_loaders import resource_json
from rpdk.jsonutils.jsonschema_flattener import (
    COMBINERS,
    ConstraintError,
    FlatteningError,
    JsonSchemaFlattener,
)


@pytest.fixture
def test_provider_schema():
    return resource_json(__name__, "data/area_definition.json")


@pytest.fixture
def flattened_schema():
    return resource_json(__name__, "data/area_definition_flattened.json")


@pytest.fixture
def flattener(test_provider_schema):
    return JsonSchemaFlattener(test_provider_schema)


PRIMITIVE_TYPES = [
    {"type": "string"},
    {"type": "integer"},
    {"type": "number"},
    {"type": "object"},
    {"type": "array"},
    {"type": "boolean"},
]
UNIQUE_KEY = "OWSAZD"


def test_flattener(flattener, flattened_schema):
    flattened_schema_map = flattener.flatten_schema()

    assert flattened_schema == flattened_schema_map


@pytest.mark.parametrize("primitive_type", PRIMITIVE_TYPES)
def test_walk_primitive_type(primitive_type):
    flattener = JsonSchemaFlattener({})
    result = flattener._walk("", primitive_type)

    assert result == primitive_type
    assert not flattener._schema_map


@pytest.mark.parametrize("primitive_type", PRIMITIVE_TYPES)
def test_walk_ref_to_primitive_type(primitive_type):
    flattener = JsonSchemaFlattener({"definitions": primitive_type})
    result = flattener._walk("", {"$ref": "#/definitions"})

    assert result == primitive_type
    assert not flattener._schema_map


def test_walk_path_already_processed():
    flattener = JsonSchemaFlattener({})
    ref = "#/properties/City"
    flattener._schema_map = {ref: None}
    result = flattener._walk(ref, None)

    assert result == {"$ref": ref}
    assert len(flattener._schema_map) == 1


def test_collapse_ref_type(flattener, flattened_schema):
    schema_path = "#/definitions/boundary/properties/box/properties/north"
    expected_collapsed_schema = {"$ref": "#/definitions/coordinate"}
    coordinate_path = "#/definitions/coordinate"

    collapsed_schema = flattener._flatten_ref_type(schema_path)

    assert expected_collapsed_schema == collapsed_schema
    assert flattener._schema_map[coordinate_path] == flattened_schema[coordinate_path]
    assert len(flattener._schema_map) == 1


def test_collapse_ref_type_nested(flattener, flattened_schema):
    schema_path = "#/definitions/boundary/properties/box"
    expected_collapsed_schema = {"$ref": "#/definitions/boundary/properties/box"}
    coordinate_path = "#/definitions/coordinate"

    collapsed_schema = flattener._flatten_ref_type(schema_path)

    assert expected_collapsed_schema == collapsed_schema
    assert flattener._schema_map[schema_path] == flattened_schema[schema_path]
    assert (
        flattener._schema_map[coordinate_path]
        == flattened_schema["#/definitions/coordinate"]
    )
    assert len(flattener._schema_map) == 2


def test_circular_reference():
    schema_flattened = resource_json(__name__, "data/circular_reference_flattened.json")
    schema = resource_json(__name__, "data/circular_reference.json")
    resolved_schema = JsonSchemaFlattener(schema).flatten_schema()
    assert resolved_schema == schema_flattened


def test_collapse_array_type(flattener, flattened_schema):
    property_key = "#/properties/city/properties/neighborhoods"
    unresolved_schema = flattener._find_subschema_by_ref(property_key)
    resolved_schema = flattener._flatten_array_type(property_key, unresolved_schema)
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
    assert flattener._schema_map[new_key] == flattened_schema[new_key]
    assert len(flattener._schema_map) == 1


def test_find_schema_from_ref(flattener, test_provider_schema):
    location_schema_expected = {
        "type": "object",
        "properties": {
            "country": {"type": "string"},
            "boundary": {"$ref": "#/definitions/boundary"},
        },
    }
    location_schema = flattener._find_subschema_by_ref("#/definitions/location")
    assert location_schema == location_schema_expected

    expected_street_schema = {"type": "string"}
    street_schema = flattener._find_subschema_by_ref(
        "#/properties/city/properties/neighborhoods/items/patternProperties/%5BA-Za-z0-9%5D%7B1%2C64%7D/properties/street"  # noqa: B950 pylint:disable=line-too-long
    )
    assert street_schema == expected_street_schema

    assert flattener._find_subschema_by_ref("#") == test_provider_schema

    ref = "#/this/is/not/a/path"
    with pytest.raises(FlatteningError) as excinfo:
        flattener._find_subschema_by_ref(ref)
    assert ref in str(excinfo.value)


@pytest.mark.parametrize("combiner", COMBINERS)
def test_flatten_combiners_single_level(combiner):
    test_schema = {"a": None, combiner: [{"b": None}, {"c": None}, {"d": None}]}
    flattener = JsonSchemaFlattener({})
    flattened = flattener._flatten_combiners("", test_schema)
    assert flattened == {"a": None, "b": None, "c": None, "d": None}


def test_flatten_multiple_combiners():
    test_schema = {"z": None}
    expected = test_schema.copy()
    for letter, combiner in zip(string.ascii_lowercase, COMBINERS):
        test_schema[combiner] = [{letter: None}]
        expected[letter] = None

    flattener = JsonSchemaFlattener({})
    flattened = flattener._flatten_combiners("", test_schema)
    assert flattened == expected


@pytest.mark.parametrize("combiner", COMBINERS)
def test_flatten_combiners_nested(combiner):
    test_schema = {"a": {"Foo": None}, combiner: [{"a": {"Bar": None}}]}
    flattener = JsonSchemaFlattener({})
    flattened = flattener._flatten_combiners("", test_schema)
    assert flattened == {"a": {"Foo": None, "Bar": None}}


@pytest.mark.parametrize("combiner", COMBINERS)
def test_flatten_combiners_overwrites(combiner):
    test_schema = {"a": None, combiner: [{"a": "Foo"}]}
    flattener = JsonSchemaFlattener({})
    flattened = flattener._flatten_combiners("", test_schema)
    assert flattened == {"a": "Foo"}


def test_flatten_combiners_with_reference():
    # test that a ref to an allOf will work when processed before OR after the allOf
    test_schema = {
        "properties": {
            "p1": {"$ref": "#/properties/p2/allOf/0"},
            "p2": {
                "allOf": [
                    {"properties": {"a2": {"type": "integer"}}},
                    {"properties": {"a2": {"type": "integer"}}},
                ]
            },
            "p3": {"$ref": "#/properties/p2/allOf/1"},
        }
    }
    expected_schema = {
        "#": {
            "properties": {
                "p1": {"$ref": "#/properties/p2/allOf/0"},
                "p2": {"$ref": "#/properties/p2"},
                "p3": {"$ref": "#/properties/p2/allOf/1"},
            }
        },
        "#/properties/p2": {"properties": {"a2": {"type": "integer"}}},
        "#/properties/p2/allOf/0": {"properties": {"a2": {"type": "integer"}}},
        "#/properties/p2/allOf/1": {"properties": {"a2": {"type": "integer"}}},
    }

    flattener = JsonSchemaFlattener(test_schema)
    schema_map = flattener.flatten_schema()
    assert schema_map == expected_schema


def test_contraint_array_additional_items_valid():
    flattener = JsonSchemaFlattener({})
    schema = {}
    result = flattener._flatten_array_type(UNIQUE_KEY, schema)
    assert result == schema


def test_contraint_array_additional_items_invalid():
    flattener = JsonSchemaFlattener({})
    schema = {"additionalItems": {"type": "string"}}
    with pytest.raises(ConstraintError) as excinfo:
        flattener._flatten_array_type(UNIQUE_KEY, schema)
    assert UNIQUE_KEY in str(excinfo.value)


def test_contraint_object_additional_properties_valid():
    flattener = JsonSchemaFlattener({})
    schema = {}
    result = flattener._flatten_object_type(UNIQUE_KEY, schema)
    assert result == schema


def test_contraint_object_additional_properties_invalid():
    flattener = JsonSchemaFlattener({})
    schema = {"additionalProperties": {"type": "string"}}
    with pytest.raises(ConstraintError) as excinfo:
        flattener._flatten_object_type(UNIQUE_KEY, schema)
    assert UNIQUE_KEY in str(excinfo.value)


def test_contraint_object_properties_and_pattern_properties():
    flattener = JsonSchemaFlattener({})
    schema = {
        "properties": {"foo": {"type": "string"}},
        "patternProperties": {"type": "string"},
    }
    with pytest.raises(ConstraintError) as excinfo:
        flattener._flatten_object_type(UNIQUE_KEY, schema)
    assert UNIQUE_KEY in str(excinfo.value)
