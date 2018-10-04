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
