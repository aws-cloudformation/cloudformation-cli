# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,protected-access
import datetime
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import botocore.exceptions
import pytest
from botocore.stub import ANY, Stubber
from dateutil.tz import tzutc

from rpdk.data_loaders import resource_yaml

EXPECTED_STACK_PARAMS = {
    "StackName": "Stack",
    "TemplateBody": "Body",
    "Capabilities": ANY,
}


@pytest.fixture
def plugin():
    from ..codegen import JavaLanguagePlugin

    return JavaLanguagePlugin()


@pytest.fixture
def project_settings(tmpdir):
    return {
        "packageName": "com.example.provider",
        "output_directory": Path(tmpdir).resolve(strict=True),
    }


def test_java_language_plugin_module_is_set(plugin):
    assert plugin.MODULE_NAME


def test_java_language_plugin_generate(plugin):
    assert plugin  # TODO


def test_initialize_maven(plugin, project_settings):
    plugin._initialize_maven(project_settings)
    pom_tree = ET.parse(str(project_settings["output_directory"] / "pom.xml"))
    namespace = {"maven": "http://maven.apache.org/POM/4.0.0"}
    package_name_prefix = pom_tree.find("maven:groupId", namespace)
    assert package_name_prefix.text == "com.example.provider"
    package_name = pom_tree.find("maven:artifactId", namespace)
    assert package_name.text == "com-example-provider"


def test_initialize_intellij(plugin, project_settings):
    project_settings["buildSystem"] = "maven"
    plugin._initialize_intellij(project_settings)

    tmp_intellij_dir = project_settings["output_directory"] / ".idea"
    misc_tree = ET.parse(str(tmp_intellij_dir / "misc.xml"))

    assert misc_tree.find("./component[@name='MavenProjectsManager']")
    assert ET.parse(str(tmp_intellij_dir / "jsonSchemas.xml"))


def test_package(plugin):
    plugin._create_or_update_stack = mock.Mock()
    plugin._get_stack_output = mock.Mock()
    plugin._package_lambda = mock.Mock()
    plugin.package("handler.path")
    template = resource_yaml(
        "rpdk.languages.java", "data/CloudFormationHandlerInfrastructure.yaml"
    )
    handler_template = resource_yaml("rpdk.languages.java", "data/Handlers.yaml")
    calls = [
        mock.call(plugin.INFRA_STACK, json.dumps(template)),
        mock.call(plugin.HANDLER_STACK, json.dumps(handler_template)),
    ]
    plugin._create_or_update_stack.assert_has_calls(calls)
    plugin._get_stack_output.assert_called_once_with(plugin.INFRA_STACK, "BucketName")


def test_create_stack_success(plugin):
    stubber = Stubber(plugin._cfn_client)
    stubber.add_response("create_stack", {}, EXPECTED_STACK_PARAMS)
    plugin._stack_wait = mock.Mock()
    with stubber:
        plugin._create_or_update_stack(
            EXPECTED_STACK_PARAMS["StackName"], EXPECTED_STACK_PARAMS["TemplateBody"]
        )


def test_create_already_exists_update_success(plugin):
    stubber = Stubber(plugin._cfn_client)
    plugin._stack_wait = mock.Mock()
    stubber.add_client_error("create_stack", "AlreadyExistsException")
    stubber.add_response("update_stack", {}, EXPECTED_STACK_PARAMS)
    with stubber:
        plugin._create_or_update_stack(
            EXPECTED_STACK_PARAMS["StackName"], EXPECTED_STACK_PARAMS["TemplateBody"]
        )


def test_create_exists_update_noop(plugin):
    stubber = Stubber(plugin._cfn_client)
    plugin._stack_wait = mock.Mock()
    stubber.add_client_error("create_stack", "AlreadyExistsException")
    stubber.add_client_error(
        "update_stack",
        "ClientError",
        "An error occurred (ValidationError) when calling the UpdateStack"
        " operation: No updates are to be performed.",
    )
    with stubber:
        plugin._create_or_update_stack(
            EXPECTED_STACK_PARAMS["StackName"], EXPECTED_STACK_PARAMS["TemplateBody"]
        )


def test_create_exists_update_fails(plugin):
    stubber = Stubber(plugin._cfn_client)
    plugin._stack_wait = mock.Mock()
    stubber.add_client_error("create_stack", "AlreadyExistsException")
    stubber.add_client_error("update_stack", "ClientError")
    with stubber, pytest.raises(botocore.exceptions.ClientError):
        plugin._create_or_update_stack(
            EXPECTED_STACK_PARAMS["StackName"], EXPECTED_STACK_PARAMS["TemplateBody"]
        )


def test_stack_wait(plugin):
    stubber = Stubber(plugin._cfn_client)
    response = {
        "Stacks": [
            {
                "StackName": EXPECTED_STACK_PARAMS["StackName"],
                "StackStatus": "CREATE_COMPLETE",
                "CreationTime": datetime.datetime(1, 1, 1, 1, 1, 1, 1, tzinfo=tzutc()),
            }
        ]
    }
    stubber.add_response("describe_stacks", response)
    with stubber:
        plugin._stack_wait(EXPECTED_STACK_PARAMS["StackName"], "stack_create_complete")


def test_package_lambda(plugin):
    # Boto stubber is not supported for upload_file.
    # https://github.com/boto/botocore/issues/974
    plugin._s3_client = mock.Mock(spec=["upload_file", "list_object_versions"])
    plugin._s3_client.list_object_versions.return_value = {
        "Versions": [{"VersionId": "SomeId"}]
    }
    template = {"Resources": {"ResourceHandler": {"Properties": {}}}}
    plugin._package_lambda("Handler.path", "BucketName", template)
    plugin._s3_client.upload_file.assert_called_with(
        "Handler.path", "BucketName", "Handler.path"
    )


def test_get_stack_output(plugin):
    stubber = Stubber(plugin._cfn_client)
    output_value = "MyValue"
    response = {
        "Stacks": [
            {
                "StackName": EXPECTED_STACK_PARAMS["StackName"],
                "Outputs": [{"OutputKey": "MyKey", "OutputValue": output_value}],
                "StackStatus": "CREATE_COMPLETE",
                "CreationTime": datetime.datetime(1, 1, 1, 1, 1, 1, 1, tzinfo=tzutc()),
            }
        ]
    }
    stubber.add_response("describe_stacks", response)
    with stubber:
        returned_output = plugin._get_stack_output(
            EXPECTED_STACK_PARAMS["StackName"], "MyKey"
        )
    assert returned_output == output_value


def test_get_stack_output_none(plugin):
    stubber = Stubber(plugin._cfn_client)
    output_value = "MyValue"
    response = {
        "Stacks": [
            {
                "StackName": EXPECTED_STACK_PARAMS["StackName"],
                "Outputs": [{"OutputKey": "MyKey", "OutputValue": output_value}],
                "StackStatus": "CREATE_COMPLETE",
                "CreationTime": datetime.datetime(1, 1, 1, 1, 1, 1, 1, tzinfo=tzutc()),
            }
        ]
    }
    stubber.add_response("describe_stacks", response)
    with stubber:
        returned_output = plugin._get_stack_output(
            EXPECTED_STACK_PARAMS["StackName"], "MyKy"
        )
    assert returned_output is None
