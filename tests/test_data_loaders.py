# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import json
from io import StringIO
from pathlib import Path
from unittest.mock import create_autospec

import jsonschema
import pkg_resources
import pytest
import yaml

from uluru.data_loaders import load_project_settings, load_resource_spec
from uluru.plugin_base import LanguagePlugin


def test_load_resource_spec_not_yaml():
    with pytest.raises(yaml.YAMLError):
        load_resource_spec(StringIO("}"))


def test_load_resource_spec_empty_is_invalid():
    with pytest.raises(jsonschema.exceptions.ValidationError):
        load_resource_spec(StringIO(""))


def test_load_resource_spec_example_spec_is_valid():
    basedir = Path(__file__).parent.parent  # tests/test_data_loaders.py
    example = basedir / "examples" / "aws-kinesis-stream.json"
    with example.open("r", encoding="utf-8") as f:
        assert load_resource_spec(f)


def yaml_s(obj):
    return StringIO(yaml.dump(obj))


@pytest.fixture
def plugin():
    mock_plugin = create_autospec(LanguagePlugin)
    mock_plugin.project_settings_defaults.return_value = pkg_resources.resource_stream(
        __name__, "data/project_defaults.yaml"
    )
    mock_plugin.project_settings_schema.return_value = json.load(
        pkg_resources.resource_stream(__name__, "data/project_schema.json")
    )
    return mock_plugin


def test_load_project_settings_defaults(plugin):
    assert load_project_settings(plugin, None)


def test_load_project_settings_user_specified_not_yaml(plugin):
    with pytest.raises(yaml.YAMLError):
        load_project_settings(plugin, StringIO("}"))


def test_load_project_settings_user_specified_valid(plugin):
    merged_settings = load_project_settings(plugin, yaml_s({"foo": "baz"}))
    assert merged_settings["foo"] == "baz"


def test_load_project_settings_user_specified_invalid(plugin):
    with pytest.raises(jsonschema.exceptions.ValidationError):
        load_project_settings(plugin, yaml_s({"foo": {}}))
