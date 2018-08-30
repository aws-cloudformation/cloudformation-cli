from io import StringIO
from pathlib import Path

import jsonschema
import pytest
import yaml

from uluru.data_loaders import load_project_settings, load_resource_spec


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
        spec = load_resource_spec(f)
    assert spec


def test_load_project_settings_java_defaults():
    assert load_project_settings("java", None)


def test_load_project_settings_java_user_specified_valid():
    user_settings = {"PackageNamePrefix": "org.my.package"}
    file_like = StringIO(yaml.dump(user_settings))
    merged_settings = load_project_settings("java", file_like)
    assert merged_settings["PackageNamePrefix"] == "org.my.package"


def test_load_project_settings_java_user_specified_not_yaml():
    with pytest.raises(yaml.YAMLError):
        load_project_settings("java", StringIO("}"))


def test_load_project_settings_java_user_specified_invalid():
    user_settings = {"PackageNamePrefix": {}}
    file_like = StringIO(yaml.dump(user_settings))
    with pytest.raises(jsonschema.exceptions.ValidationError):
        load_project_settings("java", file_like)
