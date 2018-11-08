# pylint: disable=too-few-public-methods,raising-format-tuple
import logging

from .pointer import fragment_decode, fragment_encode
from .utils import schema_merge, traverse

LOG = logging.getLogger(__name__)


class NormalizationError(Exception):
    pass


class ConstraintError(NormalizationError, ValueError):
    def __init__(self, message, path, *args):
        self.path = path
        message = message.format(*args, path=self.path)
        super().__init__(message)


class JsonSchemaNormalizer:
    """Normalize a schema into a collection of flattened objects by replacing
    inline objects with refs, and resolving refs to primitive types.

    The normalizer makes certain assumptions while processing:
    1) The schema must be an object (not simply a boolean)
    2) Each property can only be a single type. Therefore, ``anyOf``, ``allOf``,
    and ``oneOf`` are ignored/for validation purposes only
    3) Truthy ``additionalProperties`` on objects are not allowed
    4) For objects, ``properties`` and ``patternProperties`` are mutually exclusive
    5) Truthy ``additionalItems`` on arrays are not allowed
    """

    def __init__(self, schema):
        self._schema_map = {}
        self._full_schema = schema

    def collapse_and_resolve_schema(self):
        self._walk("#", self._full_schema)

        return self._schema_map

    def _walk(self, property_path, sub_schema):
        # have we already seen this path?
        if property_path in self._schema_map:
            return {"$ref": property_path}

        # work on shallow copy to avoid modifying the schema
        sub_schema = dict(sub_schema)

        # is it a reference?
        try:
            ref_path = sub_schema["$ref"]
        except KeyError:
            pass
        else:
            return self._collapse_ref_type(ref_path)

        # schemas without type are assumed to be objects
        json_type = sub_schema.get("type", "object")

        if json_type == "array":
            return self._collapse_array_type(property_path, sub_schema)

        if json_type == "object":
            return self._collapse_object_type(property_path, sub_schema)

        # for primitive types, we are done processing
        return sub_schema

    def _collapse_ref_type(self, ref_path):
        """This method normalizes a schema ref.
        * Refs to an object will have its own class, so the ref will be returned as is.
        * Refs to a primitive will be inlined into the schema, removing the ref.
        """
        if ref_path in self._schema_map:
            return {"$ref": ref_path}

        ref_schema = self._find_subschema_by_ref(ref_path)
        return self._walk(ref_path, ref_schema)

    def _collapse_array_type(self, key, sub_schema):
        # if "additionalItems" is truthy (e.g. a non-empty object), then fail
        if sub_schema.get("additionalItems"):
            raise ConstraintError("Object at '{path}' has 'additionalItems'", key)

        # if "items" are defined, each resolve each property
        try:
            items_schema = sub_schema["items"]
        except KeyError:
            pass
        else:
            sub_schema["items"] = self._walk(
                fragment_encode(["items"], key), items_schema
            )
        return sub_schema

    def _collapse_object_type(self, key, sub_schema):
        # we only care about allOf, anyOf, oneOf for object types
        sub_schema = self._flatten_combiners(key, sub_schema)

        # if "additionalProperties" is truthy (e.g. a non-empty object), then fail
        if sub_schema.get("additionalProperties"):
            raise ConstraintError("Object at '{path}' has 'additionalProperties'", key)

        # don't allow these together
        if "properties" in sub_schema and "patternProperties" in sub_schema:
            msg = (
                "Object at '{path}' has mutually exclusive "
                "'properties' and 'patternProperties'"
            )
            raise ConstraintError(msg, key)

        # if "properties" are defined, resolve each property
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
                new_properties[prop_name] = self._walk(
                    fragment_encode(["properties", prop_name], key), prop_schema
                )

            # replace properties with resolved properties
            sub_schema["properties"] = new_properties
            self._schema_map[key] = sub_schema
            return {"$ref": key}

        # if "patternProperties" are defined, resolve each property
        try:
            pattern_properties = sub_schema["patternProperties"]
        except KeyError:
            pass
        else:
            new_pattern_properties = {}
            for pattern, prop_schema in pattern_properties.items():
                new_pattern_properties[pattern] = self._walk(
                    fragment_encode(["patternProperties", pattern], key), prop_schema
                )
            sub_schema["patternProperties"] = new_pattern_properties

        return sub_schema

    def _flatten_combiners(self, key, sub_schema):
        """This method iterates through allOf, anyOf, and oneOf schemas and
        merges them all into the surrounding sub_schema"""

        for arr_key in ("allOf", "anyOf", "oneOf"):
            try:
                schema_array = sub_schema.pop(arr_key)
            except KeyError:
                continue
            for i, nested_schema in enumerate(schema_array):
                ref_path = fragment_encode([arr_key, i], key)
                ref_path_is_used = ref_path in self._schema_map
                walked_schema = self._walk(ref_path, nested_schema)

                # if no other schema is referencing the ref_path,
                # we no longer need the refkey since the properties will be squashed
                if ref_path_is_used:
                    resolved_schema = self._schema_map.get(ref_path)
                else:
                    resolved_schema = self._schema_map.pop(ref_path, walked_schema)

                schema_merge(sub_schema, resolved_schema)
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
