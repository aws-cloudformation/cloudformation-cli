# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,protected-access
import pytest

from rpdk.core.data_loaders import resource_json
from rpdk.core.jsonutils.flattener import JsonSchemaFlattener
from rpdk.java.pojo_resolver import JavaPojoResolver

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


def test_resolver_from_schema():
    test_schema = resource_json("tests", "jsonutils/data/area_definition.json")
    schema_map = JsonSchemaFlattener(test_schema).flatten_schema()
    resolver = JavaPojoResolver(schema_map, "areaDescription")
    expected_pojos = {
        "AreaDescription": {
            "areaName": "String",
            "areaId": "String",
            "location": "Location",
            "city": "City",
        },
        "Location": {"country": "String", "boundary": "Boundary"},
        "Boundary": {"box": "Box", "otherPoints": "Set<Coordinate>"},
        "Box": {
            "north": "Coordinate",
            "south": "Coordinate",
            "east": "Coordinate",
            "west": "Coordinate",
        },
        "Coordinate": {"latitude": "Float", "longitude": "Float"},
        "City": {
            "cityName": "String",
            "neighborhoods": "List<Map<String, Neighborhoods>>",
        },
        "Neighborhoods": {
            "street": "String",
            "charter": "Map<String, Object>",
            "houses": "Map<String, Float>",
        },
    }
    assert resolver.resolve_pojos() == expected_pojos


@pytest.mark.parametrize(
    "schema,result",
    (
        ({"type": "string"}, "String"),
        ({"type": "integer"}, "Integer"),
        ({"type": "boolean"}, "Boolean"),
        ({"type": "number"}, "Float"),
        ({"$ref": ("definitions", "Id")}, "Id"),
        ({"$ref": ("definitions", "Test")}, "Test"),
        ({"$ref": ("definitions", "Test", "Test")}, "Test_"),
        ({"type": "array"}, "List<Object>"),
        ({"type": "array", "items": {"type": "object"}}, "List<Map<String, Object>>"),
        ({"type": "array", "items": {"type": "string"}}, "List<String>"),
        ({"type": "array", "items": {"type": "integer"}}, "List<Integer>"),
        ({"type": "array", "items": {"type": "boolean"}}, "List<Boolean>"),
        ({"type": "array", "items": {"type": "number"}}, "List<Float>"),
        ({"type": "object"}, "Map<String, Object>"),
        ({"patternProperties": {"[A-Z]+": {"type": "string"}}}, "Map<String, String>"),
        (
            {"patternProperties": {"[A-Z]+": {"type": "integer"}}},
            "Map<String, Integer>",
        ),
        (
            {"patternProperties": {"[A-Z]+": {"type": "boolean"}}},
            "Map<String, Boolean>",
        ),
        ({"patternProperties": {"[A-Z]+": {"type": "number"}}}, "Map<String, Float>"),
        ({"patternProperties": {}}, "Map<String, Object>"),
        ({"patternProperties": {"a-z": {}, "A-Z": {}}}, "Map<String, Object>"),
    ),
)
def test_java_property_type(empty_resolver, schema, result):
    empty_resolver._ref_to_class_map = REF_TO_CLASS_MAP
    resolved_type = empty_resolver._java_property_type(schema)
    assert result == resolved_type


@pytest.mark.parametrize(
    "schema,result",
    (
        ({"type": "array"}, "List"),
        ({"type": "array", "insertionOrder": False, "uniqueItems": False}, "List"),
        ({"type": "array", "insertionOrder": True, "uniqueItems": True}, "List"),
        ({"type": "array", "insertionOrder": True}, "List"),
        ({"type": "array", "uniqueItems": True}, "Set"),
    ),
)
def test_array_class_name(empty_resolver, schema, result):
    resolved_class = empty_resolver._array_class_name(schema)
    assert result == resolved_class


@pytest.mark.parametrize(
    "ref_path,result",
    (
        (("properties", "Id"), "Id_"),
        (("definitions", "prop", "Test"), "Test__"),
        (("definitions", "prop", "Test", "items"), "Test__"),
    ),
)
def test_ref_to_class(empty_resolver, ref_path, result):
    resolved_class = empty_resolver._get_class_name_from_ref(ref_path, REF_TO_CLASS_MAP)
    assert result == resolved_class
