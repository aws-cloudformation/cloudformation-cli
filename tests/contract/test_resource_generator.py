import re
from collections.abc import Sequence

import pytest

from rpdk.core.contract.resource_generator import (
    STRING_FORMATS,
    generate_schema_strategy,
)


@pytest.mark.parametrize("schema_type", ["integer", "number"])
def test_generate_number_strategy(schema_type):
    schema = {"type": schema_type, "minimum": 0, "maximum": 16}
    strategy = generate_schema_strategy(schema)
    for i in range(100):
        assert schema["minimum"] <= strategy.example() <= schema["maximum"], i


def test_generate_string_strategy_regex():
    schema = {"type": "string", "pattern": "^foo+bar+\\Z$"}
    regex_strategy = generate_schema_strategy(schema)
    assert re.fullmatch(schema["pattern"], regex_strategy.example())


def test_generate_string_strategy_format():
    schema = {"type": "string", "format": "arn"}
    strategy = generate_schema_strategy(schema)
    assert re.fullmatch(STRING_FORMATS["arn"], strategy.example())


def test_generate_string_strategy_length():
    schema = {"type": "string", "minLength": 5, "maxLength": 10}
    strategy = generate_schema_strategy(schema)
    for i in range(100):
        assert schema["minLength"] <= len(strategy.example()) <= schema["maxLength"], i


def test_generate_string_strategy_no_constraints():
    schema = {"type": "string"}
    strategy = generate_schema_strategy(schema)
    assert isinstance(strategy.example(), str)


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
    assert len(example) >= 1
    assert isinstance(example[0], str)


def test_generate_array_strategy_multiple_items():
    schema = {"type": "array", "items": [{"type": "string"}, {"type": "integer"}]}
    example = generate_schema_strategy(schema).example()
    assert isinstance(example, Sequence)
    assert len(example) == 2
    assert isinstance(example[0], str)
    assert isinstance(example[1], int)


@pytest.mark.parametrize("combiner", ["allOf", "oneOf", "anyOf"])
def test_generate_object_strategy_simple_combiner(combiner):
    schema = {
        "type": "object",
        "properties": {"foo": {"type": "string", combiner: [{"const": "bar"}]}},
    }
    example = generate_schema_strategy(schema).example()
    assert example == {"foo": "bar"}


@pytest.mark.parametrize("combiner", ["oneOf", "anyOf"])
def test_generate_object_strategy_one_of(combiner):
    schema = {
        "type": "object",
        "properties": {
            "foo": {"type": "string", combiner: [{"const": "bar"}, {"enum": ["bar"]}]}
        },
    }
    example = generate_schema_strategy(schema).example()
    assert example == {"foo": "bar"}


def test_generate_object_strategy_all_of():
    schema = {
        "type": "object",
        "properties": {"foo": {"allOf": [{"type": "string"}, {"const": "bar"}]}},
    }
    example = generate_schema_strategy(schema).example()
    assert example == {"foo": "bar"}


def test_generate_object_strategy_properties():
    schema = {"properties": {"foo": {"type": "string", "const": "bar"}}}
    example = generate_schema_strategy(schema).example()
    assert example == {"foo": "bar"}


def test_generate_object_strategy_empty():
    schema = {}
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
