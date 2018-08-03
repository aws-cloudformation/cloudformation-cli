import json
import logging

import jsonschema
import pkg_resources
import yaml

LOG = logging.getLogger(__name__)


def load_resource_spec(resource_spec_file):
    """Load a resource provider definition from a file, and validate it."""
    try:
        resource_spec = yaml.safe_load(resource_spec_file)
    except yaml.YAMLError as e:
        LOG.error('Could not load the resource provider definition: %s', e)
        raise
        # TODO: error handling, decode errors have 'msg', 'doc', 'pos'

    with pkg_resources.resource_stream(
            __name__,
            'data/resource_provider_schema.json') as f:
        resource_spec_schema = json.load(f)

    try:
        jsonschema.validate(resource_spec, resource_spec_schema)
        # the unit tests should catch `SchemaError`/if the schema is invalid
    except jsonschema.exceptions.ValidationError as e:
        LOG.error('The resource provider definition is invalid: %s', e)
        raise  # TODO: error handling

    return resource_spec


def default_project_settings_file(language):
    filename = 'data/{}/project_defaults.yaml'.format(language)
    return pkg_resources.resource_stream(__name__, filename)


def load_project_settings(language, project_settings_file):
    """Load language-specific project settings from a file, merge them into
    the default project settings, and validate the result.

    ``project_settings_file`` can be ``None``.
    """
    with default_project_settings_file(language) as f:
        project_settings = yaml.safe_load(f)

    if project_settings_file:
        try:
            project_settings_user = yaml.safe_load(project_settings_file)
        except yaml.YAMLError as e:
            LOG.error('Could not load the project settings: %s', e)
            raise
            # TODO: error handling, decode errors have 'msg', 'doc', 'pos'
        else:
            project_settings.update(project_settings_user)
    else:
        LOG.warning(
            'Using default project settings. Provide custom project settings '
            'to further customize code generation.')

    with pkg_resources.resource_stream(
            __name__,
            'data/{}/project_schema.json'.format(language)) as f:
        project_settings_schema = json.load(f)

    try:
        jsonschema.validate(project_settings, project_settings_schema)
        # the unit tests should catch `SchemaError`/if the schema is invalid
    except jsonschema.exceptions.ValidationError as e:
        LOG.error('The project settings are invalid: %s', e)
        raise  # TODO: error handling

    return project_settings
