# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,protected-access
import xml.etree.ElementTree as ET
from unittest.mock import patch

import pytest
import yaml

from rpdk.project import Project

from ..codegen import JavaLanguagePlugin

RESOURCE = "DZQWCC"


@pytest.fixture
def project(tmpdir):
    project = Project(root=tmpdir)
    with patch.dict(
        "rpdk.plugin_registry.PLUGIN_REGISTRY",
        {"test": lambda: JavaLanguagePlugin},
        clear=True,
    ):
        project.init("AWS::Foo::{}".format(RESOURCE), "test")
    return project


def test_java_language_plugin_module_is_set():
    plugin = JavaLanguagePlugin()
    assert plugin.MODULE_NAME


def test_initialize(project):
    assert (project.root / "README.md").is_file()

    pom_tree = ET.parse(str(project.root / "pom.xml"))
    namespace = {"maven": "http://maven.apache.org/POM/4.0.0"}
    actual_group_id = pom_tree.find("maven:groupId", namespace)
    expected_group_id = "com.aws.foo.{}".format(RESOURCE.lower())
    assert actual_group_id.text == expected_group_id
    path = project.root / "Handler.yaml"
    with path.open("r", encoding="utf-8") as f:
        template = yaml.safe_load(f)

    handler_properties = template["Resources"]["ResourceHandler"]["Properties"]

    code_uri = "./target/{}-handler-1.0-SNAPSHOT.jar".format(project.hypenated_name)
    assert handler_properties["CodeUri"] == code_uri
    handler = "{}.BaseHandler::handleRequest".format(expected_group_id)
    assert handler_properties["Handler"] == handler
    assert handler_properties["Runtime"] == project._plugin.RUNTIME


def test_generate(project):
    project.load_schema()

    generated_root = project._plugin._get_generated_root(project)

    # generated root shouldn't be present
    assert not generated_root.is_dir()

    project.generate()

    test_file = generated_root / "test"
    test_file.touch()

    project.generate()

    # asserts we remove existing files in the tree
    assert not test_file.is_file()


def test_package(project):
    project.load_schema()
    project._plugin.package(project)
