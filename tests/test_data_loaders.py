# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import json
from contextlib import contextmanager
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import create_autospec, patch

import jsonschema
import pytest
import yaml
from pytest_localserver.http import Request, Response, WSGIServer

from rpdk.data_loaders import (
    load_resource_spec,
    make_validator,
    resource_json,
    resource_stream,
    resource_yaml,
)
from rpdk.plugin_base import LanguagePlugin

# Lonely continuation byte is invalid
# https://www.cl.cam.ac.uk/~mgk25/ucs/examples/UTF-8-test.txt
INVALID_UTF8 = b"\x80"


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


def test_load_resource_spec_valid_snippets():
    basedir = Path(__file__).parent.parent  # tests/test_data_loaders.py
    exampledir = basedir / "tests" / "data" / "schema" / "valid"
    for example in exampledir.glob("*.json"):
        with example.open("r", encoding="utf-8") as f:
            assert load_resource_spec(f)


def test_load_resource_spec_invalid_snippets():
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
    mock_plugin.project_settings_defaults.return_value = resource_stream(
        __name__, "data/project_defaults.yaml"
    )
    mock_plugin.project_settings_schema.return_value = resource_json(
        __name__, "data/project_schema.json"
    )
    return mock_plugin


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


def mock_pkg_resource_stream(bytes_in, func=resource_stream):
    resource_name = "data/test.utf-8"
    target = "rpdk.data_loaders.pkg_resources.resource_stream"
    with patch(target, autospec=True, return_value=BytesIO(bytes_in)) as mock_stream:
        f = func(__name__, resource_name)
    mock_stream.assert_called_once_with(__name__, resource_name)
    return f


def test_resource_stream_decoding_valid():
    emoji_santa = "🎅"
    f = mock_pkg_resource_stream(emoji_santa.encode("utf-8"))
    assert f.read() == emoji_santa


def test_resource_stream_decoding_invalid():
    f = mock_pkg_resource_stream(INVALID_UTF8)

    # stream is lazily decoded
    with pytest.raises(UnicodeDecodeError) as excinfo:
        f.read()
    assert excinfo.value.encoding == "utf-8"
    assert excinfo.value.object == INVALID_UTF8


def test_resource_stream_universal_newlines():
    f = mock_pkg_resource_stream(b"Windows\r\n")
    assert f.read() == "Windows\n"


def test_resource_stream_with_statement():
    string = "Hello, World"
    with mock_pkg_resource_stream(string.encode("utf-8")) as f:
        assert f.read() == string

    with pytest.raises(ValueError) as excinfo:
        f.read()
    assert "I/O operation on closed file" in str(excinfo.value)


def test_resource_json():
    obj = {"foo": "bar"}
    encoded = json.dumps(obj).encode("utf-8")
    result = mock_pkg_resource_stream(encoded, func=resource_json)
    assert result == obj


def test_resource_yaml():
    obj = {"foo": "bar"}
    encoded = yaml.dump(obj).encode("utf-8")
    result = mock_pkg_resource_stream(encoded, func=resource_yaml)
    assert result == obj
