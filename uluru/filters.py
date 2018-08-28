FILTER_REGISTRY = {}


def register_filter(f):
    """Registers a filter function in this module's registry, so that filters
    can be added to Jinja2 environments easily.
    """
    FILTER_REGISTRY[f.__name__] = f
    return f


@register_filter
def resource_type_name(resource_type):
    """Gets the resource name from a resource type. The resource type is
    returned if the resource type separator ("::") is not found.

    >>> resource_type_name('AWS::ECS::Instance')
    'Instance'
    """
    split_result = resource_type.split("::")
    if len(split_result) == 3:
        return split_result[2]
    return resource_type


@register_filter
def resource_service_name(resource_type):
    """Gets the service name from a resource type. The resource type is
    returned if the resource type separator ("::") is not found.

    >>> resource_service_name('AWS::ECS::Instance')
    'ECS'
    """
    split_result = resource_type.split("::")
    if len(split_result) == 3:
        return split_result[1]
    return resource_type


@register_filter
def java_class_name(import_name):
    """Gets the class name from a Java import. The full import is returned if
    no period (".") is found.

    >>> java_class_name('com.example.MyClass')
    'MyClass'
    """
    return import_name.split(".")[-1]


@register_filter
def lowercase_first_letter(s):
    """Makes the first letter of a string lowercase. Useful for creating
    lowerCamelCase variable names from UpperCamelCase strings.
    Returns an empty string if the input is empty.

    >>> lowercase_first_letter("CreateHandler")
    "createHandler"
    """
    if s:
        return s[0].lower() + s[1:]
    return ""


@register_filter
def property_type_json_to_java(schema_type):
    """Returns Java types based on the JSON type of a property.
    Currently supports the below types.
    Otherwise will return the original JSON type.
    """
    types = {
        "string": "String",
        "integer": "int",
        "boolean": "boolean",
        "number": "float",
        "array": "List",
    }
    # what add'l things to add?

    try:
        return types[schema_type]
    except TypeError:
        return schema_type["$ref"].rpartition("/")[-1] + "Model"
        # todo I realize this is pretty hacky
    except KeyError:
        return schema_type


@register_filter
def modified_from_action_type(action_type):
    """Returns a boolean (as a string) representing whether the action type of
    the handler modifies the resource. Defaults to false.

    >>> modified_from_action_type('write')
    'true'
    >>> modified_from_action_type('read')
    'false'
    >>> modified_from_action_type('')
    'false'
    """
    if action_type == "write":
        return "true"
    return "false"
