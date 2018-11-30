from collections.abc import Mapping, Sequence

from hypothesis.strategies import (
    booleans,
    characters,
    decimals,
    fixed_dictionaries,
    from_regex,
    integers,
    just,
    lists,
    nothing,
    one_of,
    text,
    tuples,
)

from ..jsonutils.utils import traverse

# TODO This resource generator handles simple cases for resource generation
# List of outstanding issues available below
# TODO https://github.com/awslabs/aws-cloudformation-rpdk/issues/118

# Arn is just a placeholder for testing
STRING_FORMATS = {
    "arn": "^arn:aws(-(cn|gov))?:[a-z-]+:(([a-z]+-)+[0-9])?:([0-9]{12})?:[^.]+$"
}


def generate_object_strategy(schema):
    try:
        one_of_schema = schema["oneOf"]
    except KeyError:
        required_properties = schema["required"]
        strategy = generate_required_properties(schema, required_properties)
    else:
        strategies = [
            generate_required_properties(schema, required_options["required"])
            for required_options in one_of_schema
        ]
        strategy = one_of(strategies)
    return strategy


def generate_required_properties(schema, required):
    strategies = {
        prop: generate_property_strategy(traverse(schema, ("properties", prop)))
        for prop in required
    }
    return fixed_dictionaries(strategies)


def generate_number_strategy(schema, strategy):
    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    return strategy(min_value=minimum, max_value=maximum)


def generate_string_strategy(schema):
    try:
        string_format = schema["format"]
    except KeyError:
        min_length = schema.get("minLength", 0)
        max_length = schema.get("maxLength")
        strategy = text(
            alphabet=characters(min_codepoint=1, blacklist_categories=("Cc", "Cs")),
            min_size=min_length,
            max_size=max_length,
        )
    else:
        strategy = from_regex(STRING_FORMATS[string_format])
    return strategy


def generate_array_strategy(array_schema):
    try:
        item_schema = array_schema["items"]
    except KeyError:
        try:
            item_schema = array_schema["contains"]
        except KeyError:
            return lists(nothing())
    if isinstance(item_schema, Sequence):
        item_strategy = [generate_property_strategy(schema) for schema in item_schema]
        # tuples let you define multiple strategies to generate elements.
        # When more than one schema for an item
        # is present, we should try to generate both
        return tuples(*item_strategy)
    item_strategy = generate_property_strategy(item_schema)
    return lists(item_strategy, min_size=1)


def generate_const_object_strategy(const):
    strategies = {key: generate_const_strategy(value) for key, value in const.items()}
    return fixed_dictionaries(strategies)


def generate_enum_strategy(enum):
    strategies = [generate_const_strategy(item) for item in enum]
    return one_of(*strategies)


def generate_const_strategy(const):
    if isinstance(const, Mapping):
        return generate_const_object_strategy(const)
    return just(const)


def generate_property_strategy(prop):
    json_type = prop.get("type", "object")

    if "const" in prop:
        strategy = generate_const_strategy(prop["const"])
    elif "enum" in prop:
        strategy = generate_enum_strategy(prop["enum"])
    elif json_type == "integer":
        strategy = generate_number_strategy(prop, integers)
    elif json_type == "number":
        strategy = generate_number_strategy(prop, decimals)
    elif json_type == "boolean":
        strategy = booleans()
    elif json_type == "string":
        try:
            regex = prop["pattern"]
        except KeyError:
            strategy = generate_string_strategy(prop)
        else:
            return from_regex(regex)
    elif json_type == "array":
        strategy = generate_array_strategy(prop)
    else:
        strategy = generate_object_strategy(prop)
    return strategy
