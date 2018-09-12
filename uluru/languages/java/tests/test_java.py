# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def plugin():
    from ..codegen import JavaLanguagePlugin

    return JavaLanguagePlugin()


@pytest.fixture
def project_settings(plugin, tmpdir):
    project_settings = yaml.safe_load(plugin.project_settings_defaults())
    project_settings["output_directory"] = Path(tmpdir).resolve(strict=True)
    return project_settings


def test_java_language_plugin_module_is_set(plugin):
    assert plugin.MODULE_NAME


def test_java_language_plugin_project_settings_defaults(plugin):
    assert yaml.safe_load(plugin.project_settings_defaults())


def test_java_language_plugin_project_settings_schema(plugin):
    assert "$schema" in plugin.project_settings_schema()


def test_java_language_plugin_generate(plugin):
    assert plugin  # TODO


def test_initialize_maven(plugin, project_settings):
    plugin._initialize_maven(project_settings)
    pom_tree = ET.parse(str(project_settings["output_directory"] / "pom.xml"))
    ns = {"maven": "http://maven.apache.org/POM/4.0.0"}
    package_name_prefix = pom_tree.find("maven:groupId", ns)
    assert package_name_prefix.text == "com.example"
    package_name = pom_tree.find("maven:artifactId", ns)
    assert package_name.text == "ResourceProviderExample"


def test_initialize_intellij(plugin, project_settings):
    project_settings["buildSystem"] = "maven"
    plugin._initialize_intellij(project_settings)

    tmp_intellij_dir = project_settings["output_directory"] / ".idea"
    misc_tree = ET.parse(str(tmp_intellij_dir / "misc.xml"))

    assert misc_tree.find("./component[@name='MavenProjectsManager']")
    assert ET.parse(str(tmp_intellij_dir / "jsonSchemas.xml"))
