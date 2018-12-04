import re
from collections.abc import Sequence

import pytest

from rpdk.contract.resource_generator import STRING_FORMATS, generate_schema_strategy


@pytest.mark.parametrize("schema_type", ["integer", "number"])
def test_generate_number_strategy(schema_type):
    schema = {"type": schema_type, "minimum": 0, "maximum": 16}
    strategy = generate_schema_strategy(schema)
    assert schema["minimum"] <= strategy.example() <= schema["maximum"]


def test_generate_string_regex_strategy():
    schema = {"type": "string", "pattern": "^foo+bar+\\Z$"}
    regex_strategy = generate_schema_strategy(schema)
    assert re.fullmatch(schema["pattern"], regex_strategy.example())


def test_generate_string_format_strategy():
    schema = {"type": "string", "format": "arn"}
    strategy = generate_schema_strategy(schema)
    assert re.fullmatch(STRING_FORMATS["arn"], strategy.example())


def test_generate_string_strategy():
    schema = {"type": "string", "minLength": 5, "maxLength": 10}
    strategy = generate_schema_strategy(schema)
    assert schema["minLength"] <= len(strategy.example()) <= schema["maxLength"]


def test_generate_boolean_strategy():
    schema = {"type": "boolean"}
    strategy = generate_schema_strategy(schema)
    assert isinstance(strategy.example(), bool)


def test_generate_array_strategy_simple():
    schema = {"type": "array"}
    strategy = generate_schema_strategy(schema)
    assert isinstance(strategy.example(), Sequence)


@pytest.mark.parametrize("item_constraint", ["items", "contains"])
def test_generate_array_strategy_items(item_constraint):
    schema = {"type": "array", item_constraint: {"type": "string"}, "minItems": 1}
    example = generate_schema_strategy(schema).example()
    assert isinstance(example, Sequence)
    assert isinstance(example[0], str)


def test_generate_array_strategy_multiple_items():
    schema = {"type": "array", "items": [{"type": "string"}, {"type": "integer"}]}
    example = generate_schema_strategy(schema).example()
    assert isinstance(example, Sequence)
    assert isinstance(example[0], str)
    assert isinstance(example[1], int)


@pytest.mark.parametrize("combiner", ["oneOf", "anyOf"])
def test_generate_one_of_object_strategy(combiner):
    schema = {
        "type": "object",
        combiner: [{"required": ["first"]}, {"required": ["second"]}],
        "properties": {"first": {"type": "boolean"}, "second": {"type": "boolean"}},
    }
    example = generate_schema_strategy(schema).example()
    try:
        value = example["first"]
    except KeyError:
        assert isinstance(example["second"], bool)
    else:
        assert isinstance(value, bool)
        with pytest.raises(KeyError):
            example["second"]


def test_generate_all_of_object_strategy():
    schema = {
        "type": "object",
        "allOf": [{"required": ["first"]}, {"required": ["second"]}],
        "properties": {"first": {"type": "boolean"}, "second": {"type": "boolean"}},
    }
    example = generate_schema_strategy(schema).example()
    assert isinstance(example["second"], bool)
    assert isinstance(example["first"], bool)


def test_generate_object_strategy():
    schema = {
        "type": "object",
        "required": ["first"],
        "properties": {"first": {"type": "boolean"}, "second": {"type": "object"}},
    }
    example = generate_schema_strategy(schema).example()
    assert isinstance(example["first"], bool)
    with pytest.raises(KeyError):
        example["second"]


def test_generate_empty_object_strategy():
    schema = {
        "type": "object",
        "properties": {"first": {"type": "object"}, "second": {"type": "object"}},
    }
    example = generate_schema_strategy(schema).example()
    assert example == {}


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "string", "const": "constTest"},
        {"type": "object", "const": {"key": "value"}},
    ],
)
def test_generate_const_strategy(schema):
    example = generate_schema_strategy(schema).example()
    assert example == schema["const"]


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "string", "enum": ["constTest", "anotherOne", "andOneMore"]},
        {"type": "object", "enum": [{"key": "value"}, {"anotherKey": "anotherValue"}]},
    ],
)
def test_generate_enum_strategy(schema):
    example = generate_schema_strategy(schema).example()
    assert example in schema["enum"]
