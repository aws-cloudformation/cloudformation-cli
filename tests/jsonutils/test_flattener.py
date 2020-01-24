# pylint: disable=protected-access
import string
from unittest.mock import patch

import pytest

from rpdk.core.data_loaders import resource_json
from rpdk.core.jsonutils.flattener import COMBINERS, JsonSchemaFlattener
from rpdk.core.jsonutils.pointer import fragment_encode
from rpdk.core.jsonutils.utils import CircularRefError, ConstraintError, FlatteningError

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
    result = flattener._walk(primitive_type, ())

    assert result == primitive_type
    assert not flattener._schema_map


@pytest.mark.parametrize("primitive_type", PRIMITIVE_TYPES)
def test_walk_ref_to_primitive(primitive_type):
    flattener = JsonSchemaFlattener({"a": primitive_type})
    result = flattener._walk({"$ref": "#/a"}, ())

    assert result == primitive_type
    assert not flattener._schema_map


@pytest.mark.parametrize("primitive_type", PRIMITIVE_TYPES)
def test_walk_ref_to_ref_to_primitive(primitive_type):
    test_schema = {"b": {"$ref": "#/c"}, "c": primitive_type}
    flattener = JsonSchemaFlattener(test_schema)
    result = flattener._walk({"$ref": "#/b"}, ())

    assert result == primitive_type
    assert not flattener._schema_map


@pytest.mark.parametrize("primitive_type", PRIMITIVE_TYPES)
def test_walk_pattern_properties_with_primitive(primitive_type):
    test_schema = {"patternProperties": {"a": primitive_type}}
    flattener = JsonSchemaFlattener({})
    result = flattener._walk(test_schema, ())

    assert result == test_schema
    assert not flattener._schema_map


@pytest.mark.parametrize("primitive_type", PRIMITIVE_TYPES)
def test_walk_array_items_with_primitive(primitive_type):
    test_schema = {"type": "array", "items": primitive_type}
    flattener = JsonSchemaFlattener({})
    result = flattener._walk(test_schema, ())

    assert result == test_schema
    assert not flattener._schema_map


@pytest.mark.parametrize("path", REF_PATHS)
def test_walk_object(path):
    test_schema = {"properties": {"a": {}}}
    flattener = JsonSchemaFlattener({})
    result = flattener._walk(test_schema, path)

    assert result == {"$ref": path}
    assert len(flattener._schema_map) == 1
    assert flattener._schema_map[path] == test_schema


@pytest.mark.parametrize("path", REF_PATHS)
def test_walk_pattern_properties_with_object(path):
    test_schema = {"patternProperties": {"a": {"properties": {"b": {}}}}}
    flattener = JsonSchemaFlattener({})
    result = flattener._walk(test_schema, path)

    ref_path = path + ("patternProperties", "a")

    assert result == {"patternProperties": {"a": {"$ref": ref_path}}}
    assert len(flattener._schema_map) == 1
    assert flattener._schema_map[ref_path] == {"properties": {"b": {}}}


@pytest.mark.parametrize("path", REF_PATHS)
def test_walk_array_items_with_object(path):
    test_schema = {"type": "array", "items": {"properties": {"b": {}}}}
    flattener = JsonSchemaFlattener({})
    result = flattener._walk(test_schema, path)

    ref_path = path + ("items",)

    expected_schema = {"type": "array", "items": {"$ref": ref_path}}

    assert result == expected_schema
    assert len(flattener._schema_map) == 1
    assert flattener._schema_map[ref_path] == {"properties": {"b": {}}}


@pytest.mark.parametrize("path", REF_PATHS)
def test_walk_nested_properties(path):
    test_schema = {"properties": {"a": {"properties": {"b": {}}}}}
    flattener = JsonSchemaFlattener({})
    result = flattener._walk(test_schema, path)

    ref_path = path + ("properties", "a")

    assert result == {"$ref": path}
    assert len(flattener._schema_map) == 2
    assert flattener._schema_map[path] == {"properties": {"a": {"$ref": ref_path}}}
    assert flattener._schema_map[ref_path] == {"properties": {"b": {}}}


def test_walk_ref_to_object():
    test_schema = {"a": {"properties": {"b": {}}}}

    flattener = JsonSchemaFlattener(test_schema)
    flattened = flattener._walk({"$ref": "#/a"}, ())

    assert flattened == {"$ref": ("a",)}
    assert len(flattener._schema_map) == 1
    assert flattener._schema_map[("a",)] == {"properties": {"b": {}}}


def test_walk_ref_to_ref_object():
    test_schema = {"b": {"$ref": "#/c"}, "c": {"properties": {"a": {}}}}
    flattener = JsonSchemaFlattener(test_schema)
    result = flattener._walk({"$ref": "#/b"}, ())

    assert result == {"$ref": ("c",)}
    assert len(flattener._schema_map) == 1
    assert flattener._schema_map[("c",)] == {"properties": {"a": {}}}


@pytest.mark.parametrize("path", REF_PATHS)
def test_walk_path_already_processed(path):
    flattener = JsonSchemaFlattener({})
    flattener._schema_map = {path: {}}
    result = flattener._walk({}, path)

    assert result == {"$ref": path}
    assert len(flattener._schema_map) == 1


@pytest.mark.parametrize(
    "path,subschema",
    (((), {"a": {"b": {"c": "d"}}}), (("a", "b"), {"c": "d"}), (("a", "b", "c"), "d")),
)
def test_find_schema_from_ref_valid_path(path, subschema):
    test_schema = {"a": {"b": {"c": "d"}}}
    flattener = JsonSchemaFlattener(test_schema)
    found, _, _ = flattener._find_subschema_by_ref(path)
    assert found == subschema


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
    flattened = flattener._flatten_combiners(test_schema, ())
    assert flattened == {"a": None, "b": None, "c": None, "d": None}


def test_flatten_multiple_combiners():
    test_schema = {"z": None}
    expected = test_schema.copy()
    for letter, combiner in zip(string.ascii_lowercase, COMBINERS):
        test_schema[combiner] = [{letter: None}]
        expected[letter] = None

    flattener = JsonSchemaFlattener({})
    flattened = flattener._flatten_combiners(test_schema, ())
    assert flattened == expected


@pytest.mark.parametrize("combiner", COMBINERS)
def test_flatten_combiners_nested(combiner):
    test_schema = {"a": {"Foo": None}, combiner: [{"a": {"Bar": None}}]}
    flattener = JsonSchemaFlattener({})
    flattened = flattener._flatten_combiners(test_schema, ())
    assert flattened == {"a": {"Foo": None, "Bar": None}}


@pytest.mark.parametrize("combiner", COMBINERS)
def test_flatten_combiners_overwrites(combiner):
    test_schema = {"a": None, combiner: [{"a": "Foo"}]}
    flattener = JsonSchemaFlattener({})
    flattened = flattener._flatten_combiners(test_schema, ())
    assert flattened == {"a": "Foo"}


@pytest.mark.parametrize("combiner", COMBINERS)
def test_flatten_combiners_no_clobber(combiner):
    # https://github.com/awslabs/aws-cloudformation-rpdk/pull/92#discussion_r231348534
    ref = ("properties", "p2", combiner, 0)
    test_schema = {
        "typeName": "AWS::Valid::TypeName",
        "properties": {
            "p1": {"$ref": fragment_encode(ref)},
            "p2": {
                combiner: [
                    {"properties": {"a2": {"type": "integer"}}},
                    {"properties": {"b1": {"type": "integer"}}},
                ]
            },
        },
    }

    flattener = JsonSchemaFlattener(test_schema)
    flattener.flatten_schema()
    assert ref in flattener._schema_map


@pytest.mark.parametrize("combiner", COMBINERS)
def test_flatten_combiners_resolve_types(combiner):
    ref = ("definitions", "obj")
    test_schema = {
        "typeName": "AWS::Valid::TypeName",
        "definitions": {"obj": {"type": "object"}},
        "properties": {
            "p": {combiner: [{"type": "string"}, {"$ref": fragment_encode(ref)}]}
        },
    }

    flattener = JsonSchemaFlattener(test_schema)
    with pytest.raises(ConstraintError) as excinfo:
        flattener.flatten_schema()
    assert "declared multiple values for 'type'" in str(excinfo.value)


@pytest.mark.parametrize("combiner", COMBINERS)
def test_flatten_combiners_resolve_types_object_by_default(combiner):
    # this should fail, since we declare an object type and string type
    # https://github.com/aws-cloudformation/aws-cloudformation-rpdk/issues/333
    ref = ("definitions", "obj")
    test_schema = {
        "typeName": "AWS::Valid::TypeName",
        "definitions": {"obj": {"properties": {"Foo": {"type": "object"}}}},
        "properties": {
            "p": {combiner: [{"type": "string"}, {"$ref": fragment_encode(ref)}]}
        },
    }

    flattener = JsonSchemaFlattener(test_schema)
    flattener.flatten_schema()
    assert ref in flattener._schema_map


@pytest.mark.parametrize("combiner", COMBINERS)
def test_flatten_combiners_resolve_types_nested_should_fail(combiner):
    # this should fail, since we declare type object and string for the same property
    # https://github.com/aws-cloudformation/aws-cloudformation-rpdk/issues/333
    ref = ("definitions", "obj")
    test_schema = {
        "typeName": "AWS::Valid::TypeName",
        "definitions": {"obj": {"properties": {"Foo": {"type": "object"}}}},
        "properties": {
            "p": {
                combiner: [
                    {"properties": {"Foo": {"type": "string"}}},
                    {"$ref": fragment_encode(ref)},
                ]
            }
        },
    }

    flattener = JsonSchemaFlattener(test_schema)
    flattener.flatten_schema()
    assert ref in flattener._schema_map
    assert ("properties", "p") in flattener._schema_map


@pytest.mark.parametrize("combiner", COMBINERS)
def test_flatten_combiners_flattened_before_merge_failed_but_should_not(combiner):
    # this should not fail, since the refs are actually compatible with each other
    # https://github.com/aws-cloudformation/aws-cloudformation-rpdk/issues/333
    ref = ("definitions", "obj")
    ref2 = ("definitions", "obj2")
    test_schema = {
        "typeName": "AWS::Valid::TypeName",
        "definitions": {
            "obj": {"properties": {"a": {"type": "object"}}},
            "obj2": {"properties": {"a": {"type": "object"}}},
        },
        "properties": {
            "p": {
                combiner: [
                    {"$ref": fragment_encode(ref)},
                    {"$ref": fragment_encode(ref2)},
                ]
            }
        },
    }

    flattener = JsonSchemaFlattener(test_schema)
    with pytest.raises(ConstraintError) as excinfo:
        flattener.flatten_schema()
    assert "declared multiple values for '$ref'" in str(excinfo.value)


def test_contraint_array_additional_items_valid():
    flattener = JsonSchemaFlattener({})
    schema = {}
    result = flattener._flatten_array_type(schema, (UNIQUE_KEY,))
    assert result == schema


def test_contraint_array_additional_items_invalid():
    flattener = JsonSchemaFlattener({})
    schema = {"additionalItems": {"type": "string"}}
    with pytest.raises(ConstraintError) as excinfo:
        flattener._flatten_array_type(schema, (UNIQUE_KEY,))
    assert UNIQUE_KEY in str(excinfo.value)


def test_contraint_object_additional_properties_valid():
    flattener = JsonSchemaFlattener({})
    schema = {}
    result = flattener._flatten_object_type(schema, (UNIQUE_KEY,))
    assert result == schema


def test_contraint_object_additional_properties_invalid():
    flattener = JsonSchemaFlattener({})
    schema = {"additionalProperties": {"type": "string"}}
    with pytest.raises(ConstraintError) as excinfo:
        flattener._flatten_object_type(schema, (UNIQUE_KEY,))
    assert UNIQUE_KEY in str(excinfo.value)


def test_contraint_object_properties_and_pattern_properties():
    flattener = JsonSchemaFlattener({})
    schema = {
        "properties": {"foo": {"type": "string"}},
        "patternProperties": {"type": "string"},
    }
    with pytest.raises(ConstraintError) as excinfo:
        flattener._flatten_object_type(schema, (UNIQUE_KEY,))
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


def test__flatten_ref_type_invalid():
    flattener = JsonSchemaFlattener({})
    patch_decode = patch(
        "rpdk.core.jsonutils.flattener.fragment_decode",
        autospec=True,
        side_effect=ValueError,
    )
    with patch_decode as mock_decode, pytest.raises(FlatteningError):
        flattener._flatten_ref_type("!")

    mock_decode.assert_called_once_with("!")


def test__flatten_ref_type_string():
    sub_schema = {"type": "string"}
    flattener = JsonSchemaFlattener({"a": sub_schema})
    ret = flattener._flatten_ref_type("#/a")
    assert ret == sub_schema


def test__flatten_ref_type_tuple():
    sub_schema = {"type": "string"}
    flattener = JsonSchemaFlattener({"a": sub_schema})
    ret = flattener._flatten_ref_type(("a",))
    assert ret == sub_schema


def test_flattener_double_processed_refs():
    """The flattener uses references to indicate objects, but these
    references are not JSON pointer URI fragments. In some cases, such references
    may be fed back into the flattener, like if object B is nested inside
    object A with a combiner (``oneOf``).

    When the combiner is processed, B is (correctly) flattened into a distinct
    object and placed in the schema map. A reference to B is returned, as a tuple
    (``{'$ref': ('properties', 'A', 'oneOf', 0, 'properties', 'B')}``), from
    ``_flatten_object_type``. So when the combiners are flattened, the result is:
    ``{'properties': {'B': {'$ref': ('properties', 'A', 'oneOf', 0, 'properties',
    'B')}}}``.

    So when `_flatten_object_type` hits the `$ref`, it's important that
    ``_flatten_ref_type`` understands tuples, which is also tested, so this test
    is for showing that such a situation occurs in a normal, well-formed schema.
    """
    test_schema = resource_json(__name__, "data/valid_refs_flattened_twice.json")

    flattener = JsonSchemaFlattener(test_schema)
    flattener.flatten_schema()
