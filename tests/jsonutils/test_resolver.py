# pylint: disable=protected-access,redefined-outer-name
import pytest

from rpdk.core.exceptions import ModelResolverError
from rpdk.core.jsonutils.resolver import (
    UNDEFINED,
    ContainerType,
    ModelResolver,
    ResolvedType,
    resolve_models,
)


def test_resolve_models():
    # want to avoid a complex test here, since it could hide missed
    # cases in the more detailed tests
    models = resolve_models({})
    assert not models


def test_resolved_type_repr():
    representation = repr(ResolvedType("foo", "bar"))
    assert "foo" in representation
    assert "bar" in representation


def test_modelresolver_empty_ref_path_results_in_model_name():
    flattened = {(): {"properties": {"foo": {"type": "string"}}}}
    resolver = ModelResolver(flattened, "ResourceModel")
    assert resolver._models == {(): "ResourceModel"}


def test_modelresolver_duplicate_model_name():
    flattened = {
        (): {"properties": {"ResourceModel": {"type": "object"}}},
        ("properties", "ResourceModel"): {"type": "object"},
    }
    with pytest.raises(ModelResolverError) as excinfo:
        ModelResolver(flattened)

    assert "ResourceModel" in str(excinfo.value)


def test_modelresolver_unique_model_name():
    unique = {
        "type": "object",
        "properties": {"foo": {"type": "string"}, "bar": {"type": "integer"}},
    }
    flattened = {
        (): {
            "definitions": {"Unique": unique},
            "properties": {"Unique": {"$ref": ("definitions", "Unique")}},
        },
        ("definitions", "Unique"): unique,
    }
    resolver = ModelResolver(flattened)
    assert resolver._models == {
        (): "ResourceModel",
        ("definitions", "Unique"): "Unique",
    }

    models = resolver.resolve_models()
    assert models == {
        "ResourceModel": {"Unique": ResolvedType(ContainerType.MODEL, "Unique")},
        "Unique": {
            "foo": ResolvedType(ContainerType.PRIMITIVE, "string"),
            "bar": ResolvedType(ContainerType.PRIMITIVE, "integer"),
        },
    }


@pytest.mark.parametrize(
    "schema,result",
    (
        ({"type": "array"}, ContainerType.LIST),
        ({"type": "array", "uniqueItems": False}, ContainerType.LIST),
        ({"type": "array", "uniqueItems": True}, ContainerType.LIST),
        ({"type": "array", "insertionOrder": False}, ContainerType.LIST),
        ({"type": "array", "insertionOrder": True}, ContainerType.LIST),
        (
            {"type": "array", "insertionOrder": True, "uniqueItems": True},
            ContainerType.LIST,
        ),
        (
            {"type": "array", "insertionOrder": True, "uniqueItems": False},
            ContainerType.LIST,
        ),
        (
            {"type": "array", "insertionOrder": False, "uniqueItems": True},
            ContainerType.SET,
        ),
        (
            {"type": "array", "insertionOrder": False, "uniqueItems": False},
            ContainerType.LIST,
        ),
    ),
)
def test_modelresolver__get_array_container_type(schema, result):
    container_type = ModelResolver._get_array_container_type(schema)
    assert container_type == result


def test_modelresolver__get_primitive_lang_type():
    sentinel = object()
    resolved_type = ModelResolver._get_primitive_lang_type(sentinel)
    assert resolved_type.container == ContainerType.PRIMITIVE
    assert resolved_type.type is sentinel


@pytest.mark.parametrize(
    "schema,result",
    (
        ({"type": "array"}, UNDEFINED),
        ({"type": "array", "items": {"type": "string"}}, "string"),
    ),
)
def test_modelresolver__get_array_lang_type(schema, result):
    resolver = ModelResolver({})
    resolved_type = resolver._get_array_lang_type(schema)
    assert resolved_type.container == ContainerType.LIST
    item_type = resolved_type.type
    assert item_type.container == ContainerType.PRIMITIVE
    assert item_type.type == result


@pytest.mark.parametrize(
    "schema,result",
    (
        ({"type": "object"}, UNDEFINED),
        ({"type": "object", "patternProperties": {}}, UNDEFINED),
        (
            {
                "type": "object",
                "patternProperties": {
                    "^S_": {"type": "string"},
                    "^I_": {"type": "integer"},
                },
            },
            UNDEFINED,
        ),
        (
            {"type": "object", "patternProperties": {"^S_": {"type": "string"}}},
            "string",
        ),
    ),
)
def test_modelresolver__get_object_lang_type(schema, result):
    resolver = ModelResolver({})
    resolved_type = resolver._get_object_lang_type(schema)
    assert resolved_type.container == ContainerType.DICT
    item_type = resolved_type.type
    assert item_type.container == ContainerType.PRIMITIVE
    assert item_type.type == result


def test_modelresolver__schema_to_lang_type_ref():
    resolver = ModelResolver({(): {}})
    assert resolver._models == {(): "ResourceModel"}
    resolved_type = resolver._schema_to_lang_type({"$ref": ()})
    assert resolved_type.container == ContainerType.MODEL
    assert resolved_type.type == "ResourceModel"


def test_modelresolver__schema_to_lang_type_array():
    # see test_modelresolver__get_array_lang_type_no_item_type
    resolver = ModelResolver({})
    resolved_type = resolver._schema_to_lang_type({"type": "array"})
    assert resolved_type.container == ContainerType.LIST
    item_type = resolved_type.type
    assert item_type.container == ContainerType.PRIMITIVE
    assert item_type.type == UNDEFINED


def test_modelresolver__schema_to_lang_type_object():
    # see test_modelresolver__get_object_lang_type_no_item_type
    resolver = ModelResolver({})
    resolved_type = resolver._schema_to_lang_type({"type": "object"})
    assert resolved_type.container == ContainerType.DICT
    item_type = resolved_type.type
    assert item_type.container == ContainerType.PRIMITIVE
    assert item_type.type == UNDEFINED


def test_modelresolver__schema_to_lang_type_undef():
    # see test_modelresolver__get_object_lang_type_no_item_type
    resolver = ModelResolver({})
    resolved_type = resolver._schema_to_lang_type({})
    assert resolved_type.container == ContainerType.DICT
    item_type = resolved_type.type
    assert item_type.container == ContainerType.PRIMITIVE
    assert item_type.type == UNDEFINED


def test_modelresolver__schema_to_lang_type_primitive():
    resolver = ModelResolver({})
    resolved_type = resolver._schema_to_lang_type({"type": "string"})
    assert resolved_type.container == ContainerType.PRIMITIVE
    assert resolved_type.type == "string"
