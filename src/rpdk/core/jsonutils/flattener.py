# pylint: disable=too-few-public-methods,raising-format-tuple
import logging

from ordered_set import OrderedSet

from .pointer import fragment_decode
from .utils import TYPE, ConstraintError, FlatteningError, schema_merge, traverse

LOG = logging.getLogger(__name__)
COMBINERS = ("oneOf", "anyOf", "allOf")


class JsonSchemaFlattener:
    """Flatten a schema into a minimal collection of  objects by replacing
    nested objects with refs, and inlining refs to primitive types.

    The flattener makes certain assumptions while processing:
    1) The schema must be an object (not simply a boolean)
    2) Each property can only be a single type.
        A) For primitive types, combiners (``anyOf``, ``allOf``, and ``oneOf``)
        B) For object types, the flattener will attempt to squash all properties
        specified in combiners into the object, and will fail if multiple types are
        declared.
    3) Truthy ``additionalProperties`` on objects are not allowed
    4) For objects, ``properties`` and ``patternProperties`` are mutually exclusive
    """

    def __init__(self, schema):
        self._schema_map = {}
        self._full_schema = schema

    def flatten_schema(self):
        self._walk(self._full_schema, ())
        return self._schema_map

    def _walk(self, sub_schema, property_path):

        # have we already seen this path?
        if property_path in self._schema_map:
            return {"$ref": property_path}

        # placeholder so as to not reprocess
        self._schema_map[property_path] = None

        # work on shallow copy to avoid modifying the schema
        sub_schema = dict(sub_schema)

        # is it a reference?
        try:
            ref_path = sub_schema["$ref"]
        except KeyError:
            # schemas without type are assumed to be objects
            json_type = sub_schema.get("type", "object")
            if json_type == "array":
                sub_schema = self._flatten_array_type(sub_schema, property_path)

            elif json_type == "object":
                sub_schema = self._flatten_object_type(sub_schema, property_path)
        else:
            sub_schema = self._flatten_ref_type(ref_path)

        # if the path was never added to the schema map, remove placeholder
        if self._schema_map[property_path] is None:
            self._schema_map.pop(property_path)

        # for primitive types, we are done processing
        return sub_schema

    def _flatten_ref_type(self, ref_path):
        """This method flattens a schema ref.
        * Refs to an object will have its own class, so the ref will be returned as is.
        * Refs to a primitive will be inlined into the schema, removing the ref.
        """
        if isinstance(ref_path, tuple):
            # we have already processed the ref, usually via flattening combiners
            ref_parts = ref_path
        else:
            try:
                ref_parts = fragment_decode(ref_path)
            except ValueError as e:
                # pylint: disable=W0707
                raise FlatteningError(
                    "Invalid ref at path '{}': {}".format(ref_path, str(e))
                )

        ref_schema, ref_parts, _ref_parent = self._find_subschema_by_ref(ref_parts)
        return self._walk(ref_schema, ref_parts)

    def _flatten_array_type(self, sub_schema, path):
        # if "additionalItems" is truthy (e.g. a non-empty object), then fail
        if sub_schema.get("additionalItems"):
            raise ConstraintError("Object at '{path}' has 'additionalItems'", path)

        # if "items" are defined, each resolve each property
        try:
            items_schema = sub_schema["items"]
        except KeyError:
            pass
        else:
            sub_schema["items"] = self._walk(items_schema, path + ("items",))
        return sub_schema

    def _flatten_object_type(self, sub_schema, path):
        # we only care about allOf, anyOf, oneOf for object types
        sub_schema = self._flatten_combiners(sub_schema, path)

        # if "additionalProperties" is truthy (e.g. a non-empty object), then fail
        if sub_schema.get("additionalProperties"):
            raise ConstraintError("Object at '{path}' has 'additionalProperties'", path)

        # don't allow these together
        if "properties" in sub_schema and "patternProperties" in sub_schema:
            msg = (
                "Object at '{path}' has mutually exclusive "
                "'properties' and 'patternProperties'"
            )
            raise ConstraintError(msg, path)

        # if "properties" are defined, resolve each property
        try:
            properties = sub_schema["properties"]
        except KeyError:
            pass
        else:
            # resolve each property schema
            new_properties = {}
            for prop_name, prop_schema in properties.items():
                new_properties[prop_name] = self._walk(
                    prop_schema, path + ("properties", prop_name)
                )

            # replace properties with resolved properties
            sub_schema["properties"] = new_properties
            self._schema_map[path] = sub_schema
            return {"$ref": path}

        # if "patternProperties" are defined, resolve each property
        try:
            pattern_properties = sub_schema["patternProperties"]
        except KeyError:
            pass
        else:
            new_pattern_properties = {}
            for pattern, prop_schema in pattern_properties.items():
                new_pattern_properties[pattern] = self._walk(
                    prop_schema, path + ("patternProperties", pattern)
                )
            sub_schema["patternProperties"] = new_pattern_properties

        return sub_schema

    def _flatten_combiners(self, sub_schema, path):
        """This method iterates through allOf, anyOf, and oneOf schemas and
        merges them all into the surrounding sub_schema"""

        for arr_key in COMBINERS:
            try:
                schema_array = sub_schema.pop(arr_key)
            except KeyError:
                pass
            else:
                for i, nested_schema in enumerate(schema_array):

                    ref_path = path + (arr_key, i)
                    ref_path_is_used = ref_path in self._schema_map
                    walked_schema = self._walk(nested_schema, ref_path)

                    # if no other schema is referencing the ref_path,
                    # we no longer need the refkey since the properties will be squashed
                    if ref_path_is_used:
                        resolved_schema = self._schema_map.get(ref_path)
                    else:
                        resolved_schema = self._schema_map.pop(ref_path, walked_schema)
                    schema_merge(sub_schema, resolved_schema, path)

        if isinstance(sub_schema.get(TYPE), OrderedSet):
            sub_schema[TYPE] = list(sub_schema[TYPE])
        return sub_schema

    def _find_subschema_by_ref(self, ref_path):
        """Outputs the section of the schema corresponding to the JSON Schema reference

        :param str ref_path: json schema ref, like "#/definitions/prop"
        :return: the subschema corresponding to the ref
        """
        try:
            return traverse(self._full_schema, ref_path)
        except (LookupError, ValueError):
            # pylint: disable=W0707
            raise FlatteningError("Invalid ref: {}".format(ref_path))
