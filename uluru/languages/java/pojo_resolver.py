""" Given a normalized schema, this class returns a map of class_names to
a set of property names|property types in Java
"""


class JavaPojoResolver:
    MODULE_NAME = __name__

    def __init__(self, normalized_schema_map, resource_type):
        self.normalized_schema_map = normalized_schema_map
        self._ref_to_class_map = self._get_ref_to_class_map(resource_type)

    def resolve_pojos(self):
        pojos = {}
        for ref_path, sub_schema in self.normalized_schema_map.items():
            class_name = self._ref_to_class_map[ref_path]
            java_property_map = {}
            for prop_name, prop_schema in sub_schema["properties"].items():
                java_property_map[prop_name] = self._java_property_type(prop_schema)
            pojos[class_name] = java_property_map
        return pojos

    def _get_ref_to_class_map(self, resource_type):
        ref_to_class_map = {"#": resource_type}
        for ref_path in self.normalized_schema_map.keys():
            if ref_path == "#":
                continue
            ref_to_class_map[ref_path] = self._get_class_name_from_ref(
                ref_path, ref_to_class_map
            )
        return ref_to_class_map

    def _get_class_name_from_ref(self, ref_path, ref_to_class_map):
        # get last element that doesn't have a ~
        class_name = next(part for part in ref_path.split("/")[::-1] if "~" not in part)

        # TODO: not sure how else we would resolve duplicate class names
        while True:
            if class_name not in ref_to_class_map.values():
                break
            class_name += "_"
        return class_name

    def _java_property_type(self, property_schema):
        if isinstance(property_schema, bool):
            # True represents a JSON type
            return "Object"

        try:
            ref_path = property_schema["$ref"]
            return self._ref_to_class_map[ref_path]
        except KeyError:
            # we are not dealing with a ref, move on
            pass

        # assumption: type is required
        json_type = property_schema["type"]

        if json_type == "array":
            return self._java_array_type(property_schema)

        if json_type == "object":
            return self._java_object_type(property_schema)

        primitive_types_map = {
            "string": "String",
            "integer": "Integer",
            "boolean": "Boolean",
            "number": "Float",
        }

        return primitive_types_map[json_type]

    def _java_array_type(self, property_schema):
        array_class_name = self._array_class_name(property_schema)
        if "items" in property_schema:
            array_items_class_name = self._java_property_type(property_schema["items"])
        else:
            array_items_class_name = "Object"

        return "{}<{}>".format(array_class_name, array_items_class_name)

    def _java_object_type(self, property_schema):
        # since all inline objects have been resolved, won't see "properties" here
        if "additionalProperties" in property_schema:
            additional_properties_class_name = self._java_property_type(
                property_schema["additionalProperties"]
            )
            return "Map<String, {}>".format(additional_properties_class_name)

        return "Map<String, Object>"  # plain old object type

    def _array_class_name(self, property_schema):
        try:
            insertion_order = property_schema["insertionOrder"]
        except KeyError:
            insertion_order = False
        try:
            unique_items = property_schema["uniqueItems"]
        except KeyError:
            unique_items = False

        if insertion_order or not unique_items:
            return "List"
        return "Set"
