import re
from collections.abc import Sequence

import pytest

from rpdk.contract.resource_generator import STRING_FORMATS, ResourceGenerator


@pytest.mark.parametrize("schema_type", ["integer", "number"])
def test_generate_number_strategy(schema_type):
    int_schema = {"type": schema_type, "minimum": 0, "maximum": 16}
    int_strategy = ResourceGenerator._generate_property_strategy(int_schema)
    generated_int = int_strategy.example()
    assert int_schema["minimum"] <= generated_int <= int_schema["maximum"]


def test_generate_string_regex_strategy():
    string_schema = {"type": "string", "pattern": "^foo+bar+\\Z$"}
    regex_strategy = ResourceGenerator._generate_property_strategy(string_schema)
    generated_string = regex_strategy.example()
    assert re.fullmatch(string_schema["pattern"], generated_string)


def test_generate_string_format_strategy():
    string_schema = {"type": "string", "format": "arn"}
    arn_strategy = ResourceGenerator._generate_property_strategy(string_schema)
    generated_string = arn_strategy.example()
    assert re.fullmatch(STRING_FORMATS["arn"], generated_string)


def test_generate_string_strategy():
    string_schema = {"type": "string", "minLength": 5, "maxLength": 10}
    string_strategy = ResourceGenerator._generate_property_strategy(string_schema)
    generated_string = string_strategy.example()
    assert (
        string_schema["minLength"]
        <= len(generated_string)
        <= string_schema["maxLength"]
    )


def test_generate_boolean_strategy():
    boolean_schema = {"type": "boolean"}
    boolean_strategy = ResourceGenerator._generate_property_strategy(boolean_schema)
    generated_boolean = boolean_strategy.example()
    assert isinstance(generated_boolean, bool)


def test_generate_array_strategy_simple():
    array_schema = {"type": "array"}
    array_strategy = ResourceGenerator._generate_property_strategy(array_schema)
    generated_list = array_strategy.example()
    assert isinstance(generated_list, Sequence)


@pytest.mark.parametrize("item_constraint", ["items", "contains"])
def test_generate_array_strategy_items(item_constraint):
    array_schema = {"type": "array", item_constraint: {"type": "string"}}
    array_strategy = ResourceGenerator._generate_property_strategy(array_schema)
    generated_list = array_strategy.example()
    assert isinstance(generated_list, Sequence)
    assert isinstance(generated_list[0], str)


def test_generate_array_strategy_multiple_items():
    array_schema = {"type": "array", "items": [{"type": "string"}, {"type": "integer"}]}
    array_strategy = ResourceGenerator._generate_property_strategy(array_schema)
    generated_list = array_strategy.example()
    assert isinstance(generated_list, Sequence)
    assert isinstance(generated_list[0], str)
    assert isinstance(generated_list[1], int)


def test_generate_one_of_object_strategy():
    object_schema = {
        "type": "object",
        "oneOf": [{"required": ["first"]}, {"required": ["second"]}],
        "properties": {"first": {"type": "boolean"}, "second": {"type": "boolean"}},
    }
    generated_object = ResourceGenerator._generate_property_strategy(
        object_schema
    ).example()
    try:
        generated_object["first"]
    except KeyError:
        assert isinstance(generated_object["second"], bool)
    else:
        assert isinstance(generated_object["first"], bool)


def test_generate_object_strategy_e2e():
    object_schema = {
        "type": "object",
        "required": ["first"],
        "properties": {"first": {"type": "boolean"}, "second": {"type": "boolean"}},
    }
    generated_object = ResourceGenerator(object_schema).generate()
    assert isinstance(generated_object["first"], bool)
    with pytest.raises(KeyError):
        generated_object["second"]
