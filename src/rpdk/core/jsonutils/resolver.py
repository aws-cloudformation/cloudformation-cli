from enum import Enum, auto

from ..exceptions import ModelResolverError
from ..filters import uppercase_first_letter
from .flattener import JsonSchemaFlattener
from .utils import BASE, fragment_encode

UNDEFINED = "undefined"
MULTIPLE = "multiple"
FORMAT_DEFAULT = "default"


class ContainerType(Enum):
    PRIMITIVE = auto()
    MODEL = auto()
    DICT = auto()
    LIST = auto()
    SET = auto()
    MULTIPLE = auto()


class ResolvedType:
    def __init__(self, container, item_type, type_format=FORMAT_DEFAULT):
        self.container = container
        self.type = item_type
        self.type_format = type_format

    def __repr__(self):
        return f"<ResolvedType({self.container}, {self.type})>"

    def __eq__(self, other):
        return self.container == other.container and self.type == other.type


class ModelResolver:
    """This class takes in a flattened schema map (output of the JsonSchemaFlattener),
    and builds a full set of models using the pseudo-types ``primitive``, ``"dict"``,
    ``"list"``, ``"set"``, and ``"model"``` for container information,
    and JSON Schema types ``"string"``, ``"integer"``, ``"boolean"``, ``"number"``,
    plus an undefined sentinel value (``"undefined"``) for value types.

    This makes it easy for plugins to map the resolved (pseudo-)types to language
    types during templating.
    """

    def __init__(self, flattened_schema_map, base_model_name="ResourceModel"):
        self.flattened_schema_map = flattened_schema_map
        self._base_model_name = base_model_name
        self._models = {}
        self._models_from_refs()

    def _models_from_refs(self):
        """Creates a model name for each ref_path in the flattened schema map."""
        for ref_path in self.flattened_schema_map.keys():
            # cannot convert this into list comprehension as self._models is used
            # during the loop
            self._models[ref_path] = self._get_model_name_from_ref(ref_path)

    def _get_model_name_from_ref(self, ref_path):
        """Given a json schema ref, returns the best guess at a model name."""
        if ref_path == ():
            return self._base_model_name

        class_name = base_class_from_ref(ref_path)
        try:
            dupe_path = next(
                path for path, name in self._models.items() if name == class_name
            )
        except StopIteration:
            return class_name

        raise ModelResolverError(
            "Model name conflict. "
            f"'{class_name}' found at {dupe_path} and {ref_path}"
        )

    def resolve_models(self):
        """Iterate through each schema and create a model mapping.

        :return: A mapping of models names and properties. Properties are
        a mapping of property names and property types.

        .. seealso:: :func:`_schema_to_lang_type`
        """
        models = {}
        for ref_path, sub_schema in self.flattened_schema_map.items():
            class_name = self._models[ref_path]
            models[class_name] = {
                prop_name: self._schema_to_lang_type(prop_schema)
                for prop_name, prop_schema in sub_schema["properties"].items()
            }
        return models

    def _schema_to_lang_type(self, property_schema):
        """Return the language-specific type for a flattened schema.

        If the schema is a ref, the class is determined from ``_models``.
        """
        try:
            ref_path = property_schema["$ref"]
        except KeyError:
            pass  # we are not dealing with a ref, move on
        else:
            return ResolvedType(ContainerType.MODEL, self._models[ref_path])

        schema_type = property_schema.get("type", "object")

        if isinstance(
            schema_type, list
        ):  # generate a generic type Object which will be casted on the client side
            if len(set(schema_type)) > 1:
                return self._get_multiple_lang_type(MULTIPLE)
            schema_type = schema_type[0]

        if schema_type == "array":
            return self._get_array_lang_type(property_schema)
        if schema_type == "object":
            return self._get_object_lang_type(property_schema)
        return self._get_primitive_lang_type(schema_type, property_schema)

    @staticmethod
    def _get_array_container_type(property_schema):
        """Return True if an array has array semantics, or False for set semantics."""
        insertion_order = property_schema.get("insertionOrder", True)
        unique_items = property_schema.get("uniqueItems", False)

        if insertion_order or not unique_items:
            return ContainerType.LIST
        return ContainerType.SET

    @staticmethod
    def _get_multiple_lang_type(schema_type):
        return ResolvedType(ContainerType.MULTIPLE, schema_type)

    @staticmethod
    def _get_primitive_lang_type(schema_type, property_schema):
        return ResolvedType(
            ContainerType.PRIMITIVE,
            schema_type,
            property_schema.get("format", FORMAT_DEFAULT),
        )

    def _get_array_lang_type(self, property_schema):
        container = self._get_array_container_type(property_schema)

        try:
            items = property_schema["items"]
        except KeyError:
            items = self._get_primitive_lang_type(UNDEFINED, property_schema)
        else:
            items = self._schema_to_lang_type(items)

        return ResolvedType(container, items)

    def _get_object_lang_type(self, property_schema):
        """Resolves an object type.

        * In JSON, objects must have string keys, so we are resolving the value type.
        * If patternProperties is defined, the value type is determined by the schema
          for the pattern. We do not care about the pattern itself, since that is only
          used for validation.
        * The object will never have nested properties, as that was taken care of by
          flattening the schema (this isn't at all obvious from the code).
        * If there are no patternProperties, it must be an arbitrary JSON type, so
          we set the value type to the UNDEFINED constant for language implementations
          to distinguish it from a JSON object.
        """
        items = self._get_primitive_lang_type(UNDEFINED, property_schema)
        try:
            pattern_properties = list(property_schema["patternProperties"].items())
        except KeyError:
            # no pattern properties == undefined type
            pass
        else:
            # multiple pattern props == bad schema definition == undefined type
            if len(pattern_properties) == 1:
                items = self._schema_to_lang_type(pattern_properties[0][1])

        return ResolvedType(ContainerType.DICT, items)


def base_class_from_ref(ref_path):
    """This method determines the class_name from a ref_path
    It uses json-schema heuristics to properly determine the class name

    >>> base_class_from_ref(("definitions", "Foo"))
    'Foo'
    >>> base_class_from_ref(("properties", "foo", "items"))
    'Foo'
    >>> base_class_from_ref(("properties", "foo", "items", "patternProperties", "a"))
    'Foo'
    >>> base_class_from_ref(("properties", "items"))
    'Items'
    >>> base_class_from_ref(("properties", "patternProperties"))
    'PatternProperties'
    >>> base_class_from_ref(("properties", "properties"))
    'Properties'
    >>> base_class_from_ref(("definitions",))
    'Definitions'
    >>> base_class_from_ref(("definitions", "properties"))
    'Properties'
    >>> base_class_from_ref(())   # doctest: +NORMALIZE_WHITESPACE
    Traceback (most recent call last):
    ...
    core.exceptions.ModelResolverError:
    Could not create a valid class from schema at '#'
    """
    parent_keywords = ("properties", "definitions")
    schema_keywords = ("items", "patternProperties", "properties")

    ref_parts = ref_path[::-1]
    ref_parts_with_root = ref_parts + (BASE,)
    for idx, elem in enumerate(ref_parts):
        parent = ref_parts_with_root[idx + 1]
        if parent in parent_keywords or (
            elem not in schema_keywords and parent != "patternProperties"
        ):
            return uppercase_first_letter(elem.rpartition("/")[2])

    raise ModelResolverError(
        "Could not create a valid class from schema at '{}'".format(
            fragment_encode(ref_path)
        )
    )


def resolve_models(schema, base_model_name="ResourceModel"):
    objects = JsonSchemaFlattener(schema).flatten_schema()
    model_resolver = ModelResolver(objects, base_model_name)
    return model_resolver.resolve_models()
