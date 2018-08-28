FILTER_REGISTRY = {}


def register_filter(f):
    """Registers a filter function in this module's registry, so that filters
    can be added to Jinja2 environments easily.
    """
    FILTER_REGISTRY[f.__name__] = f
    return f


@register_filter
def resource_type_namespace(resource_type):
    """Gets the namespace from a resource type.

    The unmodified resource type is returned if the resource type is invalid.

    >>> resource_type_namespace('AWS::ECS::Instance')
    'AWS'
    >>> resource_type_namespace('AWS::ECS')
    'AWS::ECS'
    >>> resource_type_namespace('AWS::ECS::Instance::1')
    'AWS::ECS::Instance::1'
    >>> resource_type_namespace('AWS__ECS__Instance')
    'AWS__ECS__Instance'
    """
    segments = resource_type.split("::")
    if len(segments) == 3:
        return segments[0]
    return resource_type


@register_filter
def resource_type_service(resource_type):
    """Gets the service name from a resource type.

    The unmodified resource type is returned if the resource type is invalid.

    >>> resource_type_service('AWS::ECS::Instance')
    'ECS'
    >>> resource_type_service('AWS::ECS')
    'AWS::ECS'
    >>> resource_type_service('AWS::ECS::Instance::1')
    'AWS::ECS::Instance::1'
    >>> resource_type_service('AWS__ECS__Instance')
    'AWS__ECS__Instance'
    """
    segments = resource_type.split("::")
    if len(segments) == 3:
        return segments[1]
    return resource_type


@register_filter
def resource_type_resource(resource_type):
    """Gets the resource name from a resource type.

    The unmodified resource type is returned if the resource type is invalid.

    >>> resource_type_resource('AWS::ECS::Instance')
    'Instance'
    >>> resource_type_resource('AWS::ECS')
    'AWS::ECS'
    >>> resource_type_resource('AWS::ECS::Instance::1')
    'AWS::ECS::Instance::1'
    >>> resource_type_resource('AWS__ECS__Instance')
    'AWS__ECS__Instance'
    """
    segments = resource_type.split("::")
    if len(segments) == 3:
        return segments[2]
    return resource_type


@register_filter
def java_class_name(import_name):
    """Gets the class name from a Java import. The full import is returned if
    no period (".") is found.

    >>> java_class_name('com.example.MyClass')
    'MyClass'
    >>> java_class_name('com_example_MyClass')
    'com_example_MyClass'
    >>> java_class_name('')
    ''
    """
    return import_name.rpartition(".")[2]


@register_filter
def lowercase_first_letter(string):
    """Converts the first letter of a string to lowercase.

    >>> lowercase_first_letter('CreateHandler')
    'createHandler'
    >>> lowercase_first_letter('createHandler')
    'createHandler'
    >>> lowercase_first_letter('')
    ''
    """
    if string:
        return string[0].lower() + string[1:]
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
    try:
        return types[schema_type]
    except TypeError:
        # this happens for unhashable types, in which case `schema_type`
        # should be a dictionary
        return schema_type["$ref"].rpartition("/")[2] + "Model"
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
