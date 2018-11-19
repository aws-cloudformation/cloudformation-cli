# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,protected-access
import pytest

from ..pojo_resolver import JavaPojoResolver
from .flattened_schema import FLATTENED_SCHEMA

REF_TO_CLASS_MAP = {
    ("definitions", "Id"): "Id",
    ("definitions", "Test"): "Test",
    ("definitions", "Test", "Test"): "Test_",
}


@pytest.fixture
def empty_resolver():
    return JavaPojoResolver({}, "Object")


def test_resolver():
    resolver = JavaPojoResolver(FLATTENED_SCHEMA, "areaDescription")
    expected_pojos = {
        "AreaDescription": {
            "state": "Location",
            "coordinates": "List<Coordinate>",
            "surroundingStates": "Map<String, Location>",
        },
        "Coordinate": {"lat": "Float", "long": "Float"},
        "Location": {"country": "String", "stateNumber": "Integer"},
    }

    expected_ref_map = {
        (): "AreaDescription",
        ("properties", "coordinate", "items"): "Coordinate",
        ("definitions", "location"): "Location",
    }
    assert resolver._ref_to_class_map == expected_ref_map
    pojos = resolver.resolve_pojos()

    assert pojos["AreaDescription"] == expected_pojos["AreaDescription"]
    assert pojos["Coordinate"] == expected_pojos["Coordinate"]
    assert pojos["Location"] == expected_pojos["Location"]


def test_java_property_type(empty_resolver):
    items = [
        ({"type": "string"}, "String"),
        ({"type": "integer"}, "Integer"),
        ({"type": "boolean"}, "Boolean"),
        ({"type": "number"}, "Float"),
        ({"$ref": ("definitions", "Id")}, "Id"),
        ({"$ref": ("definitions", "Test")}, "Test"),
        ({"$ref": ("definitions", "Test", "Test")}, "Test_"),
    ]
    empty_resolver._ref_to_class_map = REF_TO_CLASS_MAP
    for (property_schema, result) in items:
        assert result == empty_resolver._java_property_type(
            property_schema
        ), "Failed schema: {}".format(property_schema)


def test_array_property_type(empty_resolver):
    items = [
        ({"type": "array"}, "List<Object>"),
        ({"type": "array", "items": {"type": "object"}}, "List<Map<String, Object>>"),
        ({"type": "array", "items": {"type": "string"}}, "List<String>"),
        ({"type": "array", "items": {"type": "integer"}}, "List<Integer>"),
        ({"type": "array", "items": {"type": "boolean"}}, "List<Boolean>"),
        ({"type": "array", "items": {"type": "number"}}, "List<Float>"),
    ]
    for (property_schema, result) in items:
        assert result == empty_resolver._java_array_type(
            property_schema
        ), "Failed schema: {}".format(property_schema)


def test_object_property_type(empty_resolver):
    items = [
        ({"type": "object"}, "Map<String, Object>"),
        (get_object("string"), "Map<String, String>"),
        (get_object("integer"), "Map<String, Integer>"),
        (get_object("boolean"), "Map<String, Boolean>"),
        (get_object("number"), "Map<String, Float>"),
        ({"patternProperties": {}}, "Map<String, Object>"),
        ({"patternProperties": {"a-z": {}, "A-Z": {}}}, "Map<String, Object>"),
    ]
    for (property_schema, result) in items:
        assert result == empty_resolver._java_object_type(
            property_schema
        ), "Failed schema: {}".format(property_schema)


def get_object(schema_type):
    return {"type": "object", "patternProperties": {"[A-Z]+": {"type": schema_type}}}


def test_array_class_name(empty_resolver):
    items = [
        ({"type": "array"}, "List"),
        ({"type": "array", "insertionOrder": False, "uniqueItems": False}, "List"),
        ({"type": "array", "insertionOrder": True, "uniqueItems": True}, "List"),
        ({"type": "array", "insertionOrder": True}, "List"),
        ({"type": "array", "uniqueItems": True}, "Set"),
    ]
    for (property_schema, result) in items:
        assert result == empty_resolver._array_class_name(
            property_schema
        ), "Failed schema: {}".format(property_schema)


def test_ref_to_class(empty_resolver):
    items = [
        (("properties", "Id"), "Id_"),
        (("definitions", "prop", "Test"), "Test__"),
        (("definitions", "prop", "Test", "items"), "Test__"),
    ]
    for (ref_path, result) in items:
        assert result == empty_resolver._get_class_name_from_ref(
            ref_path, REF_TO_CLASS_MAP
        ), "Failed ref: {}".format(ref_path)
