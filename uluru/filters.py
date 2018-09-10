FILTER_REGISTRY = {}


def register_filter(f):
    """Registers a filter function in this module's registry, so that filters
    can be added to Jinja2 environments easily.
    """
    FILTER_REGISTRY[f.__name__] = f
    return f


def parse_resource_type(resource_type):
    """Splits a resource type into it's components.

    :exc:`ValueError` is raised if the resource type is invalid.

    >>> parse_resource_type('AWS::ECS::Instance')
    ['AWS', 'ECS', 'Instance']
    >>> parse_resource_type('AWS::ECS')
    Traceback (most recent call last):
    ...
    ValueError: Resource type 'AWS::ECS' is invalid
    >>> parse_resource_type('AWS__ECS__Instance')
    Traceback (most recent call last):
    ...
    ValueError: Resource type 'AWS__ECS__Instance' is invalid
    """
    segments = resource_type.split("::")
    if len(segments) != 3:
        raise ValueError("Resource type '{}' is invalid".format(resource_type))
    return segments


@register_filter
def resource_type_namespace(resource_type):
    """Gets the namespace from a resource type.

    :exc:`ValueError` is raised if the resource type is invalid, see
    :function:`parse_resource_type`.

    >>> resource_type_namespace('AWS::ECS::Instance')
    'AWS'
    """
    return parse_resource_type(resource_type)[0]


@register_filter
def resource_type_service(resource_type):
    """Gets the service name from a resource type.

    :exc:`ValueError` is raised if the resource type is invalid, see
    :function:`parse_resource_type`.

    >>> resource_type_service('AWS::ECS::Instance')
    'ECS'
    """
    return parse_resource_type(resource_type)[1]


@register_filter
def resource_type_resource(resource_type):
    """Gets the resource name from a resource type.

    :exc:`ValueError` is raised if the resource type is invalid, see
    :function:`parse_resource_type`.

    >>> resource_type_resource('AWS::ECS::Instance')
    'Instance'
    """
    return parse_resource_type(resource_type)[2]


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
    """Maps JSON schema types to Java types. If the type cannot be mapped, it
    is returned as is.

    >>> property_type_json_to_java('string')
    'String'
    >>> property_type_json_to_java('integer')
    'int'
    >>> property_type_json_to_java('boolean')
    'boolean'
    >>> property_type_json_to_java('number')
    'float'
    >>> property_type_json_to_java('array')
    'List'
    >>> property_type_json_to_java('foo')
    'foo'
    >>> property_type_json_to_java({'$ref': '#/Definitions/StreamEncryption'})
    'StreamEncryptionModel'
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


@register_filter
def package_prefix(full_package_name):
    """Maps JSON schema types to Java types. If the type cannot be mapped, it
        is returned as is.

        >>> package_prefix('com.example.test')
        'com.example'
        >>> package_prefix('example.test')
        'example'
        >>> package_prefix('com.example.this.isa.test')
        'com.example.this.isa'
        >>> package_prefix('exampletest')
        Traceback (most recent call last):
        ...
        ValueError: Package name 'exampletest' is invalid
        """
    package_segments = full_package_name.rpartition(".")
    if package_segments[0]:
        return package_segments[0]
    raise ValueError("Package name '{}' is invalid".format(full_package_name))
