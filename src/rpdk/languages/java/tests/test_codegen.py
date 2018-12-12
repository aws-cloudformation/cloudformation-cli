# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,protected-access
import xml.etree.ElementTree as ET
from unittest.mock import patch

import pytest

from rpdk.package_utils import Packager
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
    group_id = pom_tree.find("maven:groupId", namespace)
    assert group_id.text == "com.aws.foo.{}".format(RESOURCE.lower())


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
    expected_handler_path = "TestHandler.path"
    expected_arn = "HandlerArn"
    project.load_schema()

    with patch.object(Packager, "package", return_value=expected_arn) as mock_package:
        project.package(expected_handler_path)

    mock_package.assert_called_once_with(expected_handler_path)
    assert project.handler_arn == expected_arn
