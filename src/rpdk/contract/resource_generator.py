import collections.abc

from hypothesis.strategies import (
    booleans,
    characters,
    fixed_dictionaries,
    from_regex,
    integers,
    lists,
    nothing,
    one_of,
    text,
    tuples,
)

from ..jsonutils.utils import traverse

# TODO add correct regular expressions for all jsonschema string formats.
# Arn is just a placeholder for testing
STRING_FORMATS = {
    "arn": "^arn:aws(-(cn|gov))?:[a-z-]+:(([a-z]+-)+[0-9])?:([0-9]{12})?:[^.]+$"
}


class ResourceGenerator:
    def __init__(self, resource_def):
        self._strategy = self._generate_object_strategy(resource_def)

    def generate(self):
        return self._strategy.example()

    @classmethod
    def _generate_object_strategy(cls, schema):
        try:
            one_of_schema = schema["oneOf"]
        except KeyError:
            required_properties = schema["required"]
            strategy = cls._generate_required_properties(schema, required_properties)
        else:
            strategies = [
                cls._generate_required_properties(schema, required_options["required"])
                for required_options in one_of_schema
            ]
            strategy = one_of(strategies)
        return strategy

    @classmethod
    def _generate_required_properties(cls, schema, required):
        strategies = {
            prop: cls._generate_property_strategy(
                traverse(schema, ("properties", prop))
            )
            for prop in required
        }
        return fixed_dictionaries(strategies)

    @staticmethod
    def _generate_integer_strategy(int_schema):
        minimum = int_schema.get("minimum")
        maximum = int_schema.get("maximum")
        return integers(min_value=minimum, max_value=maximum)

    @staticmethod
    def _generate_string_strategy(string_schema):
        try:
            string_format = string_schema["format"]
        except KeyError:
            min_length = string_schema.get("minLength", 0)
            max_length = string_schema.get("maxLength")
            strategy = text(
                alphabet=characters(min_codepoint=1, blacklist_categories=("Cc", "Cs")),
                min_size=min_length,
                max_size=max_length,
            )
        else:
            strategy = from_regex(STRING_FORMATS[string_format])
        return strategy

    @classmethod
    def _generate_array_strategy(cls, array_schema):
        try:
            item_schema = array_schema["items"]
        except KeyError:
            return lists(nothing())
        if isinstance(item_schema, collections.abc.Sequence):
            item_strategy = [
                cls._generate_property_strategy(schema) for schema in item_schema
            ]
            # tuples let you define multiple strategies to generate elements.
            # When more than one schema for an item
            # is present, we should try to generate both
            return tuples(*item_strategy)
        item_strategy = cls._generate_property_strategy(item_schema)
        return lists(item_strategy, min_size=1)

    @classmethod
    def _generate_property_strategy(cls, prop):
        json_type = prop.get("type", "object")
        if json_type == "integer":
            strategy = cls._generate_integer_strategy(prop)
        elif json_type == "boolean":
            strategy = booleans()
        elif json_type == "string":
            try:
                regex = prop["pattern"]
            except KeyError:
                strategy = cls._generate_string_strategy(prop)
            else:
                return from_regex(regex)
        elif json_type == "array":
            strategy = cls._generate_array_strategy(prop)
        else:
            strategy = cls._generate_object_strategy(prop)
        return strategy
