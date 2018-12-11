# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,protected-access
import xml.etree.ElementTree as ET
from unittest.mock import patch

import pkg_resources
import pytest

from rpdk.project import Project

from ..codegen import JavaLanguagePlugin

RESOURCE = "DZQWCC"


@pytest.fixture
def project(tmpdir):
    return Project(root=tmpdir)


def test_java_language_plugin_module_is_set():
    plugin = JavaLanguagePlugin()
    assert plugin.MODULE_NAME


def test_initialize(project):
    with patch.dict(
        "rpdk.plugin_registry.PLUGIN_REGISTRY",
        {"test": lambda: JavaLanguagePlugin},
        clear=True,
    ):
        project.init("AWS::Foo::{}".format(RESOURCE), "test")

    assert (project.root / "README.md").is_file()

    pom_tree = ET.parse(str(project.root / "pom.xml"))
    namespace = {"maven": "http://maven.apache.org/POM/4.0.0"}
    group_id = pom_tree.find("maven:groupId", namespace)
    assert group_id.text == "com.aws.foo.{}".format(RESOURCE.lower())


def test_generate(project):
    with patch.dict(
        "rpdk.plugin_registry.PLUGIN_REGISTRY",
        {"test": lambda: JavaLanguagePlugin},
        clear=True,
    ):
        project.init("AWS::Foo::{}".format(RESOURCE), "test")

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
    with patch.dict(
        "rpdk.plugin_registry.PLUGIN_REGISTRY",
        {"test": lambda: JavaLanguagePlugin},
        clear=True,
    ):
        project.init("AWS::Foo::{}".format(RESOURCE), "test")
    project.load_schema()
    expected_bucket = "BucketName"
    expected_handler_path = "my/handler.path"
    expected_client = object()

    boto_patch = patch("boto3.client", return_value=expected_client)
    create_update_patch = patch("java.codegen.create_or_update_stack")
    stack_output_patch = patch(
        "java.codegen.get_stack_output", return_value=expected_bucket
    )
    package_patch = patch("java.codegen.package_handler")

    with boto_patch, create_update_patch as mock_create_update, (
        stack_output_patch
    ) as mock_stack_output, package_patch as mock_package:
        project.package(expected_handler_path)
    raw_template = pkg_resources.resource_string(
        "rpdk.languages.java", "data/CloudFormationHandlerInfrastructure.yaml"
    )

    mock_create_update.assert_called_once_with(
        expected_client, project._plugin.INFRA_STACK, raw_template.decode("utf-8")
    )
    mock_stack_output.assert_called_once_with(
        expected_client, project._plugin.INFRA_STACK, "BucketName"
    )
    mock_package.assert_called_with(
        expected_bucket, expected_handler_path, project._plugin.HANDLER_STACK
    )
