from io import StringIO

import jsonschema
import pytest
import yaml

from uluru.data_loaders import load_project_settings, load_resource_spec


def test_load_resource_spec_json_error():
    with pytest.raises(yaml.parser.ParserError):
        load_resource_spec(StringIO('}'))


def test_load_resource_spec_invalid_spec():
    # TODO: our spec is too lenient
    load_resource_spec(StringIO('{}'))


def test_load_resource_spec_valid_spec():
    spec = {}
    file_like = StringIO(yaml.dump(spec))
    assert load_resource_spec(file_like) == spec


def test_load_project_settings_java_defaults():
    assert load_project_settings('java', None)


def test_load_project_settings_java_user_specified_valid():
    user_settings = {'package_name_prefix': 'org.my.package'}
    file_like = StringIO(yaml.dump(user_settings))
    merged_settings = load_project_settings('java', file_like)
    assert merged_settings['package_name_prefix'] == 'org.my.package'


def test_load_project_settings_java_user_specified_invalid():
    user_settings = {'package_name_prefix': {}}
    file_like = StringIO(yaml.dump(user_settings))

    with pytest.raises(jsonschema.exceptions.ValidationError):
        load_project_settings('java', file_like)
