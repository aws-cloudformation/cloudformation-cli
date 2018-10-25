# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import json
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from unittest.mock import create_autospec

import jsonschema
import pkg_resources
import pytest
import yaml
from pytest_localserver.http import Request, Response, WSGIServer

from uluru.data_loaders import load_project_settings, load_resource_spec, make_validator
from uluru.plugin_base import LanguagePlugin


def yaml_s(obj):
    return StringIO(yaml.dump(obj))


def test_load_resource_spec_not_yaml():
    with pytest.raises(yaml.YAMLError):
        load_resource_spec(StringIO("}"))


def test_load_resource_spec_empty_is_invalid():
    with pytest.raises(jsonschema.exceptions.ValidationError):
        load_resource_spec(StringIO(""))


def test_load_resource_spec_boolean_is_invalid():
    with pytest.raises(jsonschema.exceptions.ValidationError):
        load_resource_spec(yaml_s(True))


def test_load_resource_spec_empty_object_is_invalid():
    with pytest.raises(jsonschema.exceptions.ValidationError):
        load_resource_spec(yaml_s({}))


def test_load_resource_spec_example_spec_is_valid():
    basedir = Path(__file__).parent.parent  # tests/test_data_loaders.py
    exampledir = basedir / "examples" / "schema" / "resource"
    for example in exampledir.glob("*.json"):
        with example.open("r", encoding="utf-8") as f:
            assert load_resource_spec(f)


def test_load_resource_spec_example_spec_is_invalid():
    basedir = Path(__file__).parent.parent  # tests/test_data_loaders.py
    exampledir = basedir / "tests" / "data" / "schema" / "invalid"
    for example in exampledir.glob("*.json"):
        with example.open("r", encoding="utf-8") as f:
            with pytest.raises(jsonschema.exceptions.ValidationError):
                load_resource_spec(f)


def test_load_resource_spec_remote_key_is_invalid():
    schema = {
        "typeName": "AWS::FOO::BAR",
        "properties": {"foo": {"type": "string"}},
        "remote": {},
    }
    with pytest.raises(jsonschema.exceptions.ValidationError) as excinfo:
        load_resource_spec(yaml_s(schema))
    assert "remote" in excinfo.value.message


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


@contextmanager
def wsgi_serve(application):
    server = WSGIServer(application=application)
    try:
        server.start()
        yield server
    finally:
        server.stop()


def test_make_validator_handlers_time_out():
    from time import sleep

    @Request.application
    def application(request):  # pylint: disable=unused-argument
        sleep(3)
        return Response("true", mimetype="application/json")

    with wsgi_serve(application) as server:
        with pytest.raises(jsonschema.exceptions.RefResolutionError) as excinfo:
            validator = make_validator(
                {"$ref": server.url}, base_uri="http://localhost/", timeout=0.5
            )
            validator.validate(True)
    assert "Read timed out" in str(excinfo.value)
