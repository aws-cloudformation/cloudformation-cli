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
    return resource_type.rpartition('::')[2]


@register_filter
def java_class_name(import_name):
    """Gets the class name from a Java import. The import name is returned if
    no period (".") is found.

    >>> java_class_name('com.example.MyClass')
    'MyClass'
    """
    return import_name.rpartition('.')[2]
