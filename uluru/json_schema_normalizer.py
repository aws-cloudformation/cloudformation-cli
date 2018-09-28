""" This class normalizes the json-schema by replacing inline objects with refs,
and refs to primitive types with the resolved subschema
"""
# pylint: disable=too-few-public-methods
import logging

from uluru.exceptions import InvalidSchemaError

LOG = logging.getLogger(__name__)


class JsonSchemaNormalizer:
    """ The schema_map will map json_schema paths
    to a fully resolved schema.  It uses "~" in the path to denote
    json_schema keywords, rather than an actual property
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
        if property_path in self._schema_map:
            return {"$ref": property_path}

        if isinstance(sub_schema, bool):
            return sub_schema

        if "$ref" in sub_schema:
            ref_path = sub_schema["$ref"]
            return self._collapse_ref_type(ref_path)

        try:
            json_type = sub_schema["type"]

            if json_type == "array":
                return self._collapse_array_type(property_path, sub_schema)

            if json_type == "object":
                return self._collapse_object_type(property_path, sub_schema)
        except KeyError:
            # type has not been defined, so it must be an object type
            return self._collapse_object_type(property_path, sub_schema)

        # for primitive types, we don't need to process anymore
        return sub_schema

    def _collapse_ref_type(self, ref_path):
        # if it is a ref to an object, it will have its own class
        # so we want the ref path.
        # Otherwise, we want to replace the ref with the primitive
        if ref_path in self._schema_map:
            return {"$ref": ref_path}
        ref_schema = self._find_subschema_by_ref(ref_path)
        collapsed_schema = self._collapse_and_resolve_subschema(ref_path, ref_schema)
        return collapsed_schema

    def _collapse_array_type(self, key, sub_schema):
        if "items" in sub_schema:
            items_schema = sub_schema["items"]
            sub_schema["items"] = self._collapse_and_resolve_subschema(
                key + "/~items", items_schema
            )

        return sub_schema

    def _collapse_object_type(self, key, sub_schema):
        if "properties" in sub_schema:
            # placeholder so that any references to this object know not to reprocess
            self._schema_map[key] = {}

            # resolve each property schema
            new_properties = {}
            for prop_name, prop_schema in sub_schema["properties"].items():
                new_properties[prop_name] = self._collapse_and_resolve_subschema(
                    key + "/~properties/" + prop_name, prop_schema
                )

            # replace properties with resolved properties
            sub_schema["properties"] = new_properties
            self._schema_map[key] = sub_schema
            return {"$ref": key}

        if "additionalProperties" in sub_schema:
            additional_properties_schema = sub_schema["additionalProperties"]
            sub_schema["additionalProperties"] = self._collapse_and_resolve_subschema(
                key + "/~additionalProperties", additional_properties_schema
            )

        # no properties defined, no need to create a pojo
        return sub_schema

    def _find_subschema_by_ref(self, ref_path):
        # input: json schema ref path, like "#/definitions/prop"
        # output: the subschema corresponding to that ref
        path_components = ref_path.split("/")
        if len(path_components) == 1:
            return self._full_schema
        path = path_components[1:]
        sub_schema = self._full_schema
        for key in path:
            try:
                # remove the jsonschema markers when traversing schema
                sub_schema = sub_schema[key.replace("~", "")]
            except KeyError:
                raise InvalidSchemaError("Invalid ref: {}".format(ref_path))
        return sub_schema
