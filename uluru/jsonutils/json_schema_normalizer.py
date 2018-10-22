# pylint: disable=too-few-public-methods
import logging

from .pointer import fragment_decode, fragment_encode
from .utils import traverse

LOG = logging.getLogger(__name__)


class NormalizationError(Exception):
    pass


class JsonSchemaNormalizer:
    """This class normalizes the json-schema by replacing inline objects with refs,
    and refs to primitive types with the resolved subschema. It then adds all normalized
    subschemas to a map from the fully qualified ref_path to the resolved schema. The
    goal of normalizing is to be able to create well defined classes (for Java or any
    other language).

    The normalizer makes certain assumptions while processing.
    1) provider definition schema validates that schema cannot be a boolean
    2) Each property and nested property can only be a single type.  Therefore, any use
    of anyOf, allOf, and oneOf is for validation purposes only.
    3) additionalProperties and additionalItems is not allowed
    4) properties and patternProperties are mutually exlcusive, as it would not make
    sense to have an object with some properties defined and others not -- a map of
    undefined properties would itself be a property of the object.
    """

    def __init__(self, resource_schema):
        self._schema_map = {}
        self._full_schema = resource_schema

    def collapse_and_resolve_schema(self):
        self._collapse_and_resolve_subschema("#", self._full_schema)

        return self._schema_map

    def _collapse_and_resolve_subschema(self, property_path, sub_schema):
        """Given a subschema, this method will normalize it and all of its subschemas.
        The property_path is constructed further as the schema is recursively processed.

        :param str property_path: the json schema ref path to the sub_schema
        :param dict sub_schema: the unresolved schema
        :return: a normalized schema
        """
        if property_path in self._schema_map:
            return {"$ref": property_path}

        try:
            ref_path = sub_schema["$ref"]
        except KeyError:
            pass
        else:
            return self._collapse_ref_type(ref_path)

        json_type = sub_schema.get("type", "object")

        if json_type == "array":
            return self._collapse_array_type(property_path, sub_schema)

        if json_type == "object":
            return self._collapse_object_type(property_path, sub_schema)

        return sub_schema  # for primitive types, we are done processing

    def _collapse_ref_type(self, ref_path):
        """This method normalizes a schema ref.
        * Refs to an object will have its own class, so the ref will be returned as is.
        * Refs to a primitive will be inlined into the schema, removing the ref.
        """
        if ref_path in self._schema_map:
            return {"$ref": ref_path}
        ref_schema = self._find_subschema_by_ref(ref_path)
        collapsed_schema = self._collapse_and_resolve_subschema(ref_path, ref_schema)
        return collapsed_schema

    def _collapse_array_type(self, key, sub_schema):
        """Collapses a json-schema array type schema.
        * If items is defined, its schema needs to be resolved
        """
        try:
            items_schema = sub_schema["items"]
        except KeyError:
            pass
        else:
            sub_schema["items"] = self._collapse_and_resolve_subschema(
                fragment_encode(["items"], key), items_schema
            )
        return sub_schema

    def _collapse_object_type(self, key, sub_schema):
        """Collapses a json-schema object type schema.
        * If properties are defined, each property schema needs to be resolved.
        * If patternProperties are defined, each pattern schema needs to be resolved.
        * if neither is defined, it is arbitrary JSON equivalent to a primitive
        """
        try:
            properties = sub_schema["properties"]
        except KeyError:
            pass
        else:
            # placeholder so that any references to this object know not to reprocess
            self._schema_map[key] = {}

            # resolve each property schema
            new_properties = {}
            for prop_name, prop_schema in properties.items():
                new_properties[prop_name] = self._collapse_and_resolve_subschema(
                    fragment_encode(["properties", prop_name], key), prop_schema
                )

            # replace properties with resolved properties
            sub_schema["properties"] = new_properties
            self._schema_map[key] = sub_schema
            return {"$ref": key}

        try:
            pattern_properties = sub_schema["patternProperties"]
        except KeyError:
            pass
        else:
            new_pattern_properties = {}
            for pattern, prop_schema in pattern_properties.items():
                new_pattern_properties[pattern] = self._collapse_and_resolve_subschema(
                    fragment_encode(["patternProperties", pattern], key), prop_schema
                )
            sub_schema["patternProperties"] = new_pattern_properties

        return sub_schema

    def _find_subschema_by_ref(self, ref_path):
        """Outputs the section of the schema corresponding to the JSON Schema reference

        :param str ref_path: json schema ref, like "#/definitions/prop"
        :return: the subschema corresponding to the ref
        """
        path_paths = fragment_decode(ref_path)
        try:
            return traverse(self._full_schema, path_paths)
        except (LookupError, ValueError):
            raise NormalizationError("Invalid ref: {}".format(ref_path))
