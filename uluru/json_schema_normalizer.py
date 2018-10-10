"""This class normalizes the json-schema by replacing inline objects with refs,
and refs to primitive types with the resolved subschema.
"""
# pylint: disable=too-few-public-methods
import logging

from .jsonutils.pointer import fragment_decode, fragment_encode

LOG = logging.getLogger(__name__)


class JsonSchemaNormalizer:
    """The schema_map will map json_schema paths
    to a fully resolved schema.  It uses "~" in the path to denote
    json_schema keywords, rather than an actual property.
    """

    MODULE_NAME = __name__

    def __init__(self, resource_schema):
        self._schema_map = {}
        self._full_schema = resource_schema

    def collapse_and_resolve_schema(self):
        self._collapse_and_resolve_subschema("#", self._full_schema)

        return self._schema_map

    # resolve refs and fully collapse each schema
    # pylint: disable=too-many-return-statements
    def _collapse_and_resolve_subschema(self, property_path, sub_schema):
        """Given a subschema, this method will normalize it and all of its subschemas

        :param str property_path: the json schema ref path to the sub_schema
        :param dict sub_schema: the unresolved schema
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

        # for primitive types, we don't need to process anymore
        return sub_schema

    def _collapse_ref_type(self, ref_path):
        # refs to an object will have its own class, so return the ref.
        # Otherwise, we want to replace the ref with the primitive
        if ref_path in self._schema_map:
            return {"$ref": ref_path}
        ref_schema = self._find_subschema_by_ref(ref_path)
        collapsed_schema = self._collapse_and_resolve_subschema(ref_path, ref_schema)
        return collapsed_schema

    def _collapse_array_type(self, key, sub_schema):
        try:
            items_schema = sub_schema["items"]
        except KeyError:
            pass
        else:
            sub_schema["items"] = self._collapse_and_resolve_subschema(
                fragment_encode(["~items"], key), items_schema
            )
        return sub_schema

    def _collapse_object_type(self, key, sub_schema):
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
                    fragment_encode(["~properties", prop_name], key), prop_schema
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
                    fragment_encode(["~patternProperties", "~{}".format(pattern)], key),
                    prop_schema,
                )
            sub_schema["patternProperties"] = new_pattern_properties

        return sub_schema

    def _find_subschema_by_ref(self, ref_path):
        """Outputs the section of the schema corresponding to the JSON Schema reference

        :param str ref_path: json schema ref, like "#/definitions/prop"
        :return: the subschema corresponding to the ref
        """
        path_components = fragment_decode(ref_path)
        sub_schema = self._full_schema
        for key in path_components:
            try:
                # remove our jsonschema markers when traversing schema
                sub_schema = sub_schema[key.replace("~", "")]
            except KeyError:
                raise "Invalid ref: {}".format(ref_path)
        return sub_schema
