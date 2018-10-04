# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,useless-super-delegation,protected-access
from unittest.mock import patch

import pytest
import yaml

from uluru.filters import FILTER_REGISTRY
from uluru.plugin_base import LanguagePlugin


class TestLanguagePlugin(LanguagePlugin):
    MODULE_NAME = __name__

    def project_settings_defaults(self):
        return super().project_settings_defaults()

    def project_settings_schema(self):
        return super().project_settings_schema()

    def init(self, project_settings):
        return super().init(project_settings)

    def generate(self, resource_def, project_settings):
        return super().generate(resource_def, project_settings)


@pytest.fixture
def plugin():
    return TestLanguagePlugin()


def test_language_plugin_module_not_set():
    # overriding the abstract method set means an abstract class can be instantiated
    with patch.object(LanguagePlugin, "__abstractmethods__", set()):
        plugin = LanguagePlugin()  # pylint: disable=abstract-class-instantiated
    with pytest.raises(RuntimeError):
        plugin._module_name  # pylint: disable=pointless-statement


def test_language_plugin_project_settings_defaults(plugin):
    assert yaml.safe_load(plugin.project_settings_defaults())


def test_language_plugin_project_settings_schema(plugin):
    assert "$schema" in plugin.project_settings_schema()


def test_language_plugin_generate_no_op(plugin):
    plugin.generate(None, None)


def test_language_plugin_setup_jinja_env_defaults(plugin):
    env = plugin._setup_jinja_env()
    assert env.loader
    assert env.autoescape

    for name in FILTER_REGISTRY:
        assert name in env.filters

    assert env.get_template("test.txt")


def test_language_plugin_setup_jinja_env_overrides(plugin):
    loader = object()
    autoescape = object()
    env = plugin._setup_jinja_env(autoescape=autoescape, loader=loader)
    assert env.loader is loader
    assert env.autoescape is autoescape

    for name in FILTER_REGISTRY:
        assert name in env.filters
