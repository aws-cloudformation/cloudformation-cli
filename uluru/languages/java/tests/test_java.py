# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import pytest
import yaml


@pytest.fixture
def plugin():
    from ..codegen import JavaLanguagePlugin

    return JavaLanguagePlugin()


def test_java_language_plugin_module_is_set(plugin):
    assert plugin.MODULE_NAME


def test_java_language_plugin_project_settings_defaults(plugin):
    assert yaml.safe_load(plugin.project_settings_defaults())


def test_java_language_plugin_project_settings_schema(plugin):
    assert "$schema" in plugin.project_settings_schema()


def test_java_language_plugin_generate(plugin):
    assert plugin  # TODO
