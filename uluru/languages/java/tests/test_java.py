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


@pytest.fixture
def resource_type():
    return "AWS::EC2::Instance"


def test_java_language_plugin_module_is_set(plugin):
    assert plugin.MODULE_NAME


def test_java_language_plugin_project_settings_defaults(plugin):
    assert yaml.safe_load(plugin.project_settings_defaults())


def test_java_language_plugin_project_settings_schema(plugin):
    assert "$schema" in plugin.project_settings_schema()


def test_java_language_plugin_generate(plugin):
    assert plugin  # TODO


def test_initialize_maven(plugin, resource_type, project_settings):
    plugin._initialize_maven(resource_type, project_settings)
    pom_tree = ET.parse(str(project_settings["output_directory"] / "pom.xml"))
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}

    group_id = pom_tree.find("m:groupId", ns)
    assert group_id.text == "com.uluru.provider"
    artifact_id = pom_tree.find("m:artifactId", ns)
    assert artifact_id.text == "uluru-com-uluru-provider"

    jsonschema_plugin = pom_tree.find(
        "m:build/m:plugins/m:plugin[m:groupId='org.jsonschema2pojo']",
        ns,
    )
    assert jsonschema_plugin is not None
    source_schema = jsonschema_plugin.find("m:configuration/m:sourceDirectory", ns).text
    assert source_schema == "${basedir}/Instance.json"
    target_package = jsonschema_plugin.find("m:configuration/m:targetPackage", ns).text
    assert target_package == "com.uluru.provider.model"


def test_initialize_intellij(plugin, project_settings):
    plugin._initialize_intellij(project_settings)

    tmp_intellij_dir = project_settings["output_directory"] / ".idea"
    misc_tree = ET.parse(str(tmp_intellij_dir / "misc.xml"))

    assert misc_tree.find("./component[@name='MavenProjectsManager']")
    assert ET.parse(str(tmp_intellij_dir / "jsonSchemas.xml"))
