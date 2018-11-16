# pylint: disable=protected-access
import string

import pytest

from rpdk.data_loaders import resource_json
from rpdk.jsonutils.flattener import COMBINERS, JsonSchemaFlattener
from rpdk.jsonutils.utils import CircularRefError, ConstraintError, FlatteningError

from .area_definition_flattened import AREA_DEFINITION_FLATTENED

UNIQUE_KEY = "OWSAZD"

PRIMITIVE_TYPES = (
    pytest.param({"type": "string"}, id="string"),
    pytest.param({"type": "integer"}, id="integer"),
    pytest.param({"type": "number"}, id="number"),
    pytest.param({"type": "object"}, id="object"),
    pytest.param({"type": "array"}, id="array"),
    pytest.param({"type": "boolean"}, id="boolean"),
    pytest.param({"patternProperties": {"a": {}}}, id="patternProperties"),
    pytest.param({"type": "array", "items": {}}, id="array_items"),
)
REF_PATHS = ((), ("definitions",), ("definitions", "a"))
CIRCULAR_SCHEMAS = (
    pytest.param({"properties": {"a": {"$ref": "#/properties/a"}}}, id="self"),
    pytest.param(
        {
            "properties": {
                "a": {"$ref": "#/properties/z"},
                "z": {"$ref": "#/properties/a"},
            }
        },
        id="each_other",
    ),
    pytest.param(
        {
            "properties": {
                "a": {"$ref": "#/properties/b"},
                "b": {"$ref": "#/properties/c"},
                "c": {"$ref": "#/properties/a"},
            }
        },
        id="indirect",
    ),
    pytest.param(
        {
            "properties": {
                "a": {"$ref": "#/properties/b"},
                "b": {"properties": {"a": {"$ref": "#/properties/a"}}},
            }
        },
        id="nested",
    ),
)


@pytest.mark.parametrize("primitive_type", PRIMITIVE_TYPES)
def test_walk_primitive_type(primitive_type):
    flattener = JsonSchemaFlattener({})
    result = flattener._walk((), primitive_type)

    assert result == primitive_type
    assert not flattener._schema_map


@pytest.mark.parametrize("primitive_type", PRIMITIVE_TYPES)
def test_walk_ref_to_primitive(primitive_type):
    flattener = JsonSchemaFlattener({"a": primitive_type})
    result = flattener._walk((), {"$ref": "#/a"})

    assert result == primitive_type
    assert not flattener._schema_map


@pytest.mark.parametrize("primitive_type", PRIMITIVE_TYPES)
def test_walk_ref_to_ref_to_primitive(primitive_type):
    test_schema = {"b": {"$ref": "#/c"}, "c": primitive_type}
    flattener = JsonSchemaFlattener(test_schema)
    result = flattener._walk((), {"$ref": "#/b"})

    assert result == primitive_type
    assert not flattener._schema_map


@pytest.mark.parametrize("primitive_type", PRIMITIVE_TYPES)
def test_walk_pattern_properties_with_primitive(primitive_type):
    test_schema = {"patternProperties": {"a": primitive_type}}
    flattener = JsonSchemaFlattener({})
    result = flattener._walk((), test_schema)

    assert result == test_schema
    assert not flattener._schema_map


@pytest.mark.parametrize("primitive_type", PRIMITIVE_TYPES)
def test_walk_array_items_with_primitive(primitive_type):
    test_schema = {"type": "array", "items": primitive_type}
    flattener = JsonSchemaFlattener({})
    result = flattener._walk((), test_schema)

    assert result == test_schema
    assert not flattener._schema_map


@pytest.mark.parametrize("path", REF_PATHS)
def test_walk_object(path):
    test_schema = {"properties": {"a": {}}}
    flattener = JsonSchemaFlattener({})
    result = flattener._walk(path, test_schema)

    assert result == {"$ref": path}
    assert len(flattener._schema_map) == 1
    assert flattener._schema_map[path] == test_schema


@pytest.mark.parametrize("path", REF_PATHS)
def test_walk_pattern_properties_with_object(path):
    test_schema = {"patternProperties": {"a": {"properties": {"b": {}}}}}
    flattener = JsonSchemaFlattener({})
    result = flattener._walk(path, test_schema)

    ref_path = path + ("patternProperties", "a")

    assert result == {"patternProperties": {"a": {"$ref": ref_path}}}
    assert len(flattener._schema_map) == 1
    assert flattener._schema_map[ref_path] == {"properties": {"b": {}}}


@pytest.mark.parametrize("path", REF_PATHS)
def test_walk_array_items_with_object(path):
    test_schema = {"type": "array", "items": {"properties": {"b": {}}}}
    flattener = JsonSchemaFlattener({})
    result = flattener._walk(path, test_schema)

    ref_path = path + ("items",)

    expected_schema = {"type": "array", "items": {"$ref": ref_path}}

    assert result == expected_schema
    assert len(flattener._schema_map) == 1
    assert flattener._schema_map[ref_path] == {"properties": {"b": {}}}


@pytest.mark.parametrize("path", REF_PATHS)
def test_walk_nested_properties(path):
    test_schema = {"properties": {"a": {"properties": {"b": {}}}}}
    flattener = JsonSchemaFlattener({})
    result = flattener._walk(path, test_schema)

    ref_path = path + ("properties", "a")

    assert result == {"$ref": path}
    assert len(flattener._schema_map) == 2
    assert flattener._schema_map[path] == {"properties": {"a": {"$ref": ref_path}}}
    assert flattener._schema_map[ref_path] == {"properties": {"b": {}}}


def test_walk_ref_to_object():
    test_schema = {"a": {"properties": {"b": {}}}}

    flattener = JsonSchemaFlattener(test_schema)
    flattened = flattener._walk((), {"$ref": "#/a"})

    assert flattened == {"$ref": ("a",)}
    assert len(flattener._schema_map) == 1
    assert flattener._schema_map[("a",)] == {"properties": {"b": {}}}


def test_walk_ref_to_ref_object():
    test_schema = {"b": {"$ref": "#/c"}, "c": {"properties": {"a": {}}}}
    flattener = JsonSchemaFlattener(test_schema)
    result = flattener._walk((), {"$ref": "#/b"})

    assert result == {"$ref": ("c",)}
    assert len(flattener._schema_map) == 1
    assert flattener._schema_map[("c",)] == {"properties": {"a": {}}}


@pytest.mark.parametrize("path", REF_PATHS)
def test_walk_path_already_processed(path):
    flattener = JsonSchemaFlattener({})
    flattener._schema_map = {path: {}}
    result = flattener._walk(path, {})

    assert result == {"$ref": path}
    assert len(flattener._schema_map) == 1


@pytest.mark.parametrize(
    "path,subschema",
    (((), {"a": {"b": {"c": "d"}}}), (("a", "b"), {"c": "d"}), (("a", "b", "c"), "d")),
)
def test_find_schema_from_ref(path, subschema):
    test_schema = {"a": {"b": {"c": "d"}}}
    flattener = JsonSchemaFlattener(test_schema)
    assert flattener._find_subschema_by_ref(path) == subschema


def test_find_schema_from_ref_invalid_path():
    flattener = JsonSchemaFlattener({"a": "b"})
    ref = ("b",)
    with pytest.raises(FlatteningError) as excinfo:
        flattener._find_subschema_by_ref(ref)
    assert str(ref) in str(excinfo.value)


@pytest.mark.parametrize("combiner", COMBINERS)
def test_flatten_combiners_single_level(combiner):
    test_schema = {"a": None, combiner: [{"b": None}, {"c": None}, {"d": None}]}
    flattener = JsonSchemaFlattener({})
    flattened = flattener._flatten_combiners((), test_schema)
    assert flattened == {"a": None, "b": None, "c": None, "d": None}


def test_flatten_multiple_combiners():
    test_schema = {"z": None}
    expected = test_schema.copy()
    for letter, combiner in zip(string.ascii_lowercase, COMBINERS):
        test_schema[combiner] = [{letter: None}]
        expected[letter] = None

    flattener = JsonSchemaFlattener({})
    flattened = flattener._flatten_combiners((), test_schema)
    assert flattened == expected


@pytest.mark.parametrize("combiner", COMBINERS)
def test_flatten_combiners_nested(combiner):
    test_schema = {"a": {"Foo": None}, combiner: [{"a": {"Bar": None}}]}
    flattener = JsonSchemaFlattener({})
    flattened = flattener._flatten_combiners((), test_schema)
    assert flattened == {"a": {"Foo": None, "Bar": None}}


@pytest.mark.parametrize("combiner", COMBINERS)
def test_flatten_combiners_overwrites(combiner):
    test_schema = {"a": None, combiner: [{"a": "Foo"}]}
    flattener = JsonSchemaFlattener({})
    flattened = flattener._flatten_combiners((), test_schema)
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
        (): {
            "properties": {
                "p1": {"$ref": ("properties", "p2", "allOf", "0")},
                "p2": {"$ref": ("properties", "p2")},
                "p3": {"$ref": ("properties", "p2", "allOf", "1")},
            }
        },
        ("properties", "p2"): {"properties": {"a2": {"type": "integer"}}},
        ("properties", "p2", "allOf", "0"): {"properties": {"a2": {"type": "integer"}}},
        ("properties", "p2", "allOf", "1"): {"properties": {"a2": {"type": "integer"}}},
    }

    flattener = JsonSchemaFlattener(test_schema)
    schema_map = flattener.flatten_schema()
    assert schema_map == expected_schema


def test_contraint_array_additional_items_valid():
    flattener = JsonSchemaFlattener({})
    schema = {}
    result = flattener._flatten_array_type((UNIQUE_KEY,), schema)
    assert result == schema


def test_contraint_array_additional_items_invalid():
    flattener = JsonSchemaFlattener({})
    schema = {"additionalItems": {"type": "string"}}
    with pytest.raises(ConstraintError) as excinfo:
        flattener._flatten_array_type((UNIQUE_KEY,), schema)
    assert UNIQUE_KEY in str(excinfo.value)


def test_contraint_object_additional_properties_valid():
    flattener = JsonSchemaFlattener({})
    schema = {}
    result = flattener._flatten_object_type((UNIQUE_KEY,), schema)
    assert result == schema


def test_contraint_object_additional_properties_invalid():
    flattener = JsonSchemaFlattener({})
    schema = {"additionalProperties": {"type": "string"}}
    with pytest.raises(ConstraintError) as excinfo:
        flattener._flatten_object_type((UNIQUE_KEY,), schema)
    assert UNIQUE_KEY in str(excinfo.value)


def test_contraint_object_properties_and_pattern_properties():
    flattener = JsonSchemaFlattener({})
    schema = {
        "properties": {"foo": {"type": "string"}},
        "patternProperties": {"type": "string"},
    }
    with pytest.raises(ConstraintError) as excinfo:
        flattener._flatten_object_type((UNIQUE_KEY,), schema)
    assert UNIQUE_KEY in str(excinfo.value)


def test_flattener_full_example():
    test_schema = resource_json(__name__, "data/area_definition.json")

    flattener = JsonSchemaFlattener(test_schema)
    flattened = flattener.flatten_schema()

    assert flattened == AREA_DEFINITION_FLATTENED


@pytest.mark.parametrize("test_schema", CIRCULAR_SCHEMAS)
def test_circular_reference(test_schema):
    flattener = JsonSchemaFlattener(test_schema)
    with pytest.raises(CircularRefError) as excinfo:
        flattener.flatten_schema()
    assert "#/properties/a" in str(excinfo.value)
