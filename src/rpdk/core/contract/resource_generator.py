import logging
from collections.abc import Sequence

from hypothesis.strategies import (
    booleans,
    builds,
    characters,
    fixed_dictionaries,
    floats,
    from_regex,
    integers,
    just,
    lists,
    nothing,
    one_of,
    text,
    tuples,
)

from ..jsonutils.utils import schema_merge

LOG = logging.getLogger(__name__)

# TODO This resource generator handles simple cases for resource generation
# List of outstanding issues available below
# https://github.com/aws-cloudformation/aws-cloudformation-rpdk/issues/118

# Arn is just a placeholder for testing
STRING_FORMATS = {
    "arn": "^arn:aws(-(cn|gov))?:[a-z-]+:(([a-z]+-)+[0-9])?:([0-9]{12})?:[^.]+$"
}

NEG_INF = float("-inf")
POS_INF = float("inf")


def generate_schema_strategy(schema):
    if "allOf" in schema:
        return generate_all_of_strategy(schema)
    if "oneOf" in schema:
        return generate_one_of_strategy(schema, "oneOf")
    if "anyOf" in schema:
        return generate_one_of_strategy(schema, "anyOf")
    return generate_primitive_strategy(schema)


def generate_one_of_strategy(schema, combiner):
    one_of_schemas = schema.pop(combiner)
    strategies = [
        generate_schema_strategy(schema_merge(schema.copy(), one_of_schema, ""))
        for one_of_schema in one_of_schemas
    ]
    return one_of(*strategies)


def generate_all_of_strategy(schema):
    all_of_schemas = schema.pop("allOf")
    for all_of_schema in all_of_schemas:
        schema_merge(schema, all_of_schema, ())
    return generate_schema_strategy(schema)


def generate_primitive_strategy(schema):
    json_type = schema.get("type", "object")

    if "const" in schema:
        strategy = just(schema["const"])
    elif "enum" in schema:
        strategies = [just(item) for item in schema["enum"]]
        strategy = one_of(*strategies)
    elif json_type == "integer":
        strategy = generate_integer_strategy(schema)
    elif json_type == "number":
        strategy = generate_float_strategy(schema)
    elif json_type == "boolean":
        strategy = booleans()
    elif json_type == "string":
        strategy = generate_string_strategy(schema)
    elif json_type == "array":
        strategy = generate_array_strategy(schema)
    else:
        strategy = generate_object_strategy(schema)
    return strategy


def generate_object_strategy(schema):
    try:
        props = schema["properties"]
    except KeyError:
        return builds(dict)

    return fixed_dictionaries(
        {
            prop: generate_schema_strategy(sub_schema)
            for prop, sub_schema in props.items()
        }
    )


def generate_array_strategy(schema):
    min_items = schema.get("minItems", 0)
    max_items = schema.get("maxItems", None)
    try:
        item_schemas = schema["items"]
    except KeyError:
        try:
            item_schemas = schema["contains"]
        except KeyError:
            return lists(nothing())
    if isinstance(item_schemas, Sequence):
        item_strategy = [generate_schema_strategy(schema) for schema in item_schemas]
        # tuples let you define multiple strategies to generate elements.
        # When more than one schema for an item
        # is present, we should try to generate both
        return tuples(*item_strategy)
    item_strategy = generate_schema_strategy(item_schemas)
    return lists(item_strategy, min_size=min_items, max_size=max_items)


def _float_minimum(schema):
    try:
        minimum = schema["minimum"]
    except KeyError:
        exclude_min = True
        minimum = schema.get("exclusiveMinimum", NEG_INF)
    else:
        exclude_min = False
        if "exclusiveMinimum" in schema:  # pragma: no cover
            LOG.warning("found exclusiveMinimum used with minimum")
    return minimum, exclude_min


def _float_maximum(schema):
    try:
        maximum = schema["maximum"]
    except KeyError:
        exclude_max = True
        maximum = schema.get("exclusiveMaximum", POS_INF)
    else:
        exclude_max = False
        if "exclusiveMaximum" in schema:  # pragma: no cover
            LOG.warning("found exclusiveMaximum used with maximum")
    return maximum, exclude_max


def generate_float_strategy(schema):
    # minimum and/or maximum are set to -inf/+inf (exclusive) if they are not
    # supplied, to avoid generating -inf/inf/NaN values. these are not
    # serialize-able according to JSON, but Python will and this causes
    # downstream errors
    minimum, exclude_min = _float_minimum(schema)
    maximum, exclude_max = _float_maximum(schema)

    # TODO: multipleOf
    # https://github.com/aws-cloudformation/aws-cloudformation-rpdk/issues/118
    if "multipleOf" in schema:  # pragma: no cover
        LOG.warning("found multipleOf, which is currently unsupported")

    return floats(
        min_value=minimum,
        exclude_min=exclude_min,
        max_value=maximum,
        exclude_max=exclude_max,
        allow_nan=False,
    )


def _integer_minimum(schema):
    try:
        minimum = schema["minimum"]
    except KeyError:
        try:
            # for exclusive, value > min, or value >= (min + 1)
            minimum = schema["exclusiveMinimum"] + 1
        except KeyError:
            minimum = None
    else:
        if "exclusiveMinimum" in schema:  # pragma: no cover
            LOG.warning("found exclusiveMinimum used with minimum")
    return minimum


def _integer_maximum(schema):
    try:
        maximum = schema["maximum"]
    except KeyError:
        try:
            # for exclusive, value < min, or value <= (min - 1)
            maximum = schema["exclusiveMaximum"] - 1
        except KeyError:
            maximum = None
    else:
        if "exclusiveMaximum" in schema:  # pragma: no cover
            LOG.warning("found exclusiveMaximum used with maximum")
    return maximum


def generate_integer_strategy(schema):
    minimum = _integer_minimum(schema)
    maximum = _integer_maximum(schema)

    # TODO: multipleOf
    # https://github.com/aws-cloudformation/aws-cloudformation-rpdk/issues/118
    if "multipleOf" in schema:  # pragma: no cover
        LOG.warning("found multipleOf, which is currently unsupported")

    return integers(min_value=minimum, max_value=maximum)


def generate_string_strategy(schema):
    try:
        string_format = schema["format"]
    except KeyError:
        try:
            regex = schema["pattern"]
        except KeyError:
            min_length = schema.get("minLength", 0)
            max_length = schema.get("maxLength")
            return text(
                alphabet=characters(min_codepoint=1, blacklist_categories=("Cc", "Cs")),
                min_size=min_length,
                max_size=max_length,
            )

        # Issues in regex patterns can lead to subtle bugs. Also log `repr`,
        # which makes escaped characters more obvious (unicode, whitespace)
        LOG.debug("regex pattern %s/'%s'", repr(regex), regex)

        if "minLength" in schema:  # pragma: no cover
            LOG.warning("found minLength used with pattern")
        if "maxLength" in schema:  # pragma: no cover
            LOG.warning("found maxLength used with pattern")
        return from_regex(regex)

    if "pattern" in schema:  # pragma: no cover
        LOG.warning("found pattern used with format")
    if "minLength" in schema:  # pragma: no cover
        LOG.warning("found minLength used with format")
    if "maxLength" in schema:  # pragma: no cover
        LOG.warning("found maxLength used with format")

    regex = STRING_FORMATS[string_format]
    return from_regex(regex)
