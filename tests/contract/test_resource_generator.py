import re
from collections.abc import Sequence
from math import isnan

import pytest

from rpdk.core.contract.resource_generator import (
    NEG_INF,
    POS_INF,
    STRING_FORMATS,
    ResourceGenerator,
    terminate_regex,
)


def test_terminate_regex_end_of_line_like_a_normal_person():
    original_regex = r"^[a-zA-Z0-9]{1,219}$"
    assert re.match(original_regex, "dfqh3eqefhq\n")
    assert re.match(original_regex, "dfqh3eqefhq")
    modified_regex = terminate_regex(original_regex)
    assert not re.match(modified_regex, "dfqh3eqefhq\n")
    assert re.match(modified_regex, "dfqh3eqefhq")


def test_terminate_regex_no_termination_needed():
    original_regex = r"^[a-zA-Z0-9]{1,219}\Z"
    assert terminate_regex(original_regex) == original_regex


@pytest.mark.parametrize("schema_type", ["integer", "number"])
def test_generate_number_strategy_inclusive(schema_type):
    inc_min = 0
    inc_max = 16
    schema = {"type": schema_type, "minimum": inc_min, "maximum": inc_max}
    strategy = ResourceGenerator(schema).generate_schema_strategy(schema)
    for i in range(100):
        example = strategy.example()
        assert inc_min <= example <= inc_max, i


@pytest.mark.parametrize("schema_type", ["integer", "number"])
def test_generate_number_strategy_exclusive(schema_type):
    exc_min = 0
    exc_max = 16
    schema = {
        "type": schema_type,
        "exclusiveMinimum": exc_min,
        "exclusiveMaximum": exc_max,
    }
    strategy = ResourceGenerator(schema).generate_schema_strategy(schema)
    for i in range(100):
        assert exc_min < strategy.example() < exc_max, i


def test_generate_number_strategy_no_inf_or_nan():
    schema = {"type": "number"}
    strategy = ResourceGenerator(schema).generate_schema_strategy(schema)
    for i in range(100):
        example = strategy.example()
        assert example != POS_INF, i
        assert example != NEG_INF, i
        assert not isnan(example), i


def test_generate_string_strategy_regex():
    schema = {"type": "string", "pattern": "^foo+bar+\\Z$"}
    regex_strategy = ResourceGenerator(schema).generate_schema_strategy(schema)
    assert re.fullmatch(schema["pattern"], regex_strategy.example())


def test_generate_string_strategy_format():
    schema = {"type": "string", "format": "arn"}
    strategy = ResourceGenerator(schema).generate_schema_strategy(schema)
    assert re.fullmatch(STRING_FORMATS["arn"], strategy.example())


def test_generate_string_strategy_length():
    schema = {"type": "string", "minLength": 5, "maxLength": 10}
    strategy = ResourceGenerator(schema).generate_schema_strategy(schema)
    for i in range(100):
        assert schema["minLength"] <= len(strategy.example()) <= schema["maxLength"], i


def test_generate_string_strategy_no_constraints():
    schema = {"type": "string"}
    strategy = ResourceGenerator(schema).generate_schema_strategy(schema)
    assert isinstance(strategy.example(), str)


def test_generate_boolean_strategy():
    schema = {"type": "boolean"}
    strategy = ResourceGenerator(schema).generate_schema_strategy(schema)
    assert isinstance(strategy.example(), bool)


def test_generate_array_strategy_simple():
    schema = {"type": "array"}
    strategy = ResourceGenerator(schema).generate_schema_strategy(schema)
    assert isinstance(strategy.example(), Sequence)


@pytest.mark.parametrize("item_constraint", ["items", "contains"])
def test_generate_array_strategy_items(item_constraint):
    schema = {"type": "array", item_constraint: {"type": "string"}, "minItems": 1}
    example = ResourceGenerator(schema).generate_schema_strategy(schema).example()
    assert isinstance(example, Sequence)
    assert len(example) >= 1
    assert isinstance(example[0], str)


def test_generate_array_strategy_multiple_items():
    schema = {"type": "array", "items": [{"type": "string"}, {"type": "integer"}]}
    example = ResourceGenerator(schema).generate_schema_strategy(schema).example()
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
    example = ResourceGenerator(schema).generate_schema_strategy(schema).example()
    assert example == {"foo": "bar"}


@pytest.mark.parametrize("combiner", ["oneOf", "anyOf"])
def test_generate_object_strategy_one_of(combiner):
    schema = {
        "type": "object",
        "properties": {
            "foo": {"type": "string", combiner: [{"const": "bar"}, {"enum": ["bar"]}]}
        },
    }
    example = ResourceGenerator(schema).generate_schema_strategy(schema).example()
    assert example == {"foo": "bar"}


def test_generate_object_strategy_all_of():
    schema = {
        "type": "object",
        "properties": {"foo": {"allOf": [{"type": "string"}, {"const": "bar"}]}},
    }
    example = ResourceGenerator(schema).generate_schema_strategy(schema).example()
    assert example == {"foo": "bar"}


def test_generate_object_strategy_properties():
    schema = {"properties": {"foo": {"type": "string", "const": "bar"}}}
    example = ResourceGenerator(schema).generate_schema_strategy(schema).example()
    assert example == {"foo": "bar"}


def test_generate_object_strategy_empty():
    schema = {}
    example = ResourceGenerator(schema).generate_schema_strategy(schema).example()
    assert example == {}


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "string", "const": "constTest"},
        {"type": "object", "const": {"key": "value"}},
    ],
)
def test_generate_const_strategy(schema):
    example = ResourceGenerator(schema).generate_schema_strategy(schema).example()
    assert example == schema["const"]


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "string", "enum": ["constTest", "anotherOne", "andOneMore"]},
        {"type": "object", "enum": [{"key": "value"}, {"anotherKey": "anotherValue"}]},
    ],
)
def test_generate_enum_strategy(schema):
    example = ResourceGenerator(schema).generate_schema_strategy(schema).example()
    assert example in schema["enum"]


def test_generate_strategy_with_refs():
    schema = {
        "properties": {"foo": {"$ref": "#/definitions/Reference"}},
        "definitions": {"Reference": {"type": "integer"}},
    }
    example = ResourceGenerator(schema).generate_schema_strategy(schema).example()
    assert isinstance(example["foo"], int)
