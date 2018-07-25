import json

import jsonschema
import pkg_resources


def load_resource_spec(resource_spec_file):
    """Load a resource specification from a file, and validate it."""
    try:
        resource_spec = json.load(resource_spec_file)
    except json.JSONDecodeError as e:
        print(e)
        raise
        # TODO: error handling, decode errors have 'msg', 'doc', 'pos'

    resource_spec_schema = json.load(pkg_resources.resource_stream(
        __name__, 'data/resource_specification_schema.json'))

    try:
        jsonschema.validate(resource_spec, resource_spec_schema)
        # the unit tests should catch `SchemaError`/if the schema is invalid
    except jsonschema.exceptions.ValidationError as e:
        print(e)
        raise  # TODO: error handling

    return resource_spec


def load_project_settings(language, project_settings_file):
    """Load language-specific project settings from a file, merge them into
    the default project settings, and validate the result.

    ``project_settings_file`` can be ``None`.
    """
    project_settings = json.load(pkg_resources.resource_stream(
        __name__, 'data/{}/project_defaults.json'.format(language)))

    if project_settings_file:
        try:
            project_settings_user = json.load(project_settings_file)
        except json.JSONDecodeError as e:
            print(e)
            raise
            # TODO: error handling, decode errors have 'msg', 'doc', 'pos'
        else:
            project_settings.update(project_settings_user)

    project_settings_schema = json.load(pkg_resources.resource_stream(
        __name__, 'data/{}/project_schema.json'.format(language)))

    try:
        jsonschema.validate(project_settings, project_settings_schema)
        # the unit tests should catch `SchemaError`/if the schema is invalid
    except jsonschema.exceptions.ValidationError as e:
        print(e)
        raise  # TODO: error handling

    return project_settings
