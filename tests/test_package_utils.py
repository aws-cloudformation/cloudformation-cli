# pylint: disable=redefined-outer-name
import datetime
import logging
from unittest.mock import patch

import boto3
import botocore.exceptions
import pkg_resources
import pytest
from awscli.customizations.cloudformation.deploy import DeployCommand
from awscli.customizations.cloudformation.exceptions import ChangeEmptyError
from awscli.customizations.cloudformation.package import PackageCommand
from botocore.stub import ANY, Stubber
from dateutil.tz import tzutc

from rpdk.package_utils import (
    HANDLER_ARN_KEY,
    HANDLER_PARAMS,
    HANDLER_TEMPLATE_PATH,
    INFRA_STACK_NAME,
    NO_UPDATES_ERROR_MESSAGE,
    OutputNotFoundError,
    Packager,
)

EXPECTED_STACK_NAME = "Stack"
EXPECTED_TEMPLATE_BODY = "Body"
EXPECTED_STACK_CAPS = ANY

EXPECTED_STACK_PARAMS = {
    "StackName": EXPECTED_STACK_NAME,
    "TemplateBody": EXPECTED_TEMPLATE_BODY,
    "Capabilities": EXPECTED_STACK_CAPS,
}

EXPECTED_BUCKET = "TestBucket"
EXPECTED_TEMPLATE_PATH = "TestTemplate.path"
EXPECTED_HANDLER_ARN = "TestHandlerArn"

OUTPUT_VALUE = "MyValue"
OUTPUT_KEY = "MyKey"
FAKE_DATETIME = datetime.datetime(1, 1, 1, 1, 1, 1, 1, tzinfo=tzutc())


@pytest.fixture
def packager():
    client = boto3.client(
        "cloudformation", aws_access_key_id="NOTHING", aws_secret_access_key="NOTHING"
    )
    return Packager(client)


def test_create_stack_doesnt_exist(caplog, packager):
    stubber = Stubber(packager.client)
    stubber.add_response("create_stack", {}, EXPECTED_STACK_PARAMS)
    wait_patch = patch.object(Packager, "stack_wait", autospec=True)
    caplog.set_level(logging.INFO)
    with stubber, wait_patch:
        packager.create_or_update_stack(EXPECTED_STACK_NAME, EXPECTED_TEMPLATE_BODY)
    stubber.assert_no_pending_responses()
    last_record = caplog.records[-1]

    assert all(s in last_record.message for s in (EXPECTED_STACK_NAME, "created"))


def test_create_already_exists_update_success(caplog, packager):
    stubber = Stubber(packager.client)

    stubber.add_client_error("create_stack", "AlreadyExistsException")
    stubber.add_response("update_stack", {}, EXPECTED_STACK_PARAMS)
    wait_patch = patch.object(Packager, "stack_wait", autospec=True)
    caplog.set_level(logging.INFO)
    with stubber, wait_patch:
        packager.create_or_update_stack(EXPECTED_STACK_NAME, EXPECTED_TEMPLATE_BODY)
    stubber.assert_no_pending_responses()
    last_record = caplog.records[-1]
    assert all(s in last_record.message for s in (EXPECTED_STACK_NAME, "updated"))


def test_create_exists_update_noop(caplog, packager):
    stubber = Stubber(packager.client)
    stubber.add_client_error("create_stack", "AlreadyExistsException")
    stubber.add_client_error(
        "update_stack",
        "ClientError",
        "An error occurred (ValidationError) when calling the UpdateStack"
        " operation: No updates are to be performed.",
    )
    wait_patch = patch.object(Packager, "stack_wait", autospec=True)
    caplog.set_level(logging.INFO)

    with stubber, wait_patch:
        packager.create_or_update_stack(EXPECTED_STACK_NAME, EXPECTED_TEMPLATE_BODY)

    last_record = caplog.records[-1]
    assert all(
        s in last_record.message
        for s in (EXPECTED_STACK_NAME, NO_UPDATES_ERROR_MESSAGE)
    )
    stubber.assert_no_pending_responses()


def test_create_exists_update_fails(packager):
    stubber = Stubber(packager.client)
    stubber.add_client_error("create_stack", "AlreadyExistsException")
    stubber.add_client_error("update_stack", "ClientError")
    wait_patch = patch.object(Packager, "stack_wait", autospec=True)
    with stubber, wait_patch, pytest.raises(botocore.exceptions.ClientError):
        packager.create_or_update_stack(EXPECTED_STACK_NAME, EXPECTED_TEMPLATE_BODY)
    stubber.assert_no_pending_responses()


def test_stack_wait(packager):
    stubber = Stubber(packager.client)
    response = {
        "Stacks": [
            {
                "StackName": EXPECTED_STACK_NAME,
                "StackStatus": "CREATE_COMPLETE",
                "CreationTime": FAKE_DATETIME,
            }
        ]
    }
    stubber.add_response("describe_stacks", response)
    with stubber:
        packager.stack_wait(EXPECTED_STACK_NAME, "stack_create_complete")
    stubber.assert_no_pending_responses()


def test_package_handler(packager):
    package = patch.object(PackageCommand, "_run_main", return_value=0)
    deploy = patch.object(DeployCommand, "_run_main", return_value=0)
    output = patch.object(
        Packager,
        "get_stack_outputs",
        return_value={HANDLER_ARN_KEY: EXPECTED_HANDLER_ARN},
    )

    with package as mock_package, deploy as mock_deploy, output as mock_output:
        packager.package_handler(
            EXPECTED_BUCKET, EXPECTED_TEMPLATE_PATH, EXPECTED_STACK_NAME, {}
        )
    mock_output.assert_called_once()
    mock_package.assert_called_once()
    mock_deploy.assert_called_once()

    package_namespace = mock_package.call_args[0][0]
    assert package_namespace.s3_bucket == EXPECTED_BUCKET
    assert package_namespace.template_file == EXPECTED_TEMPLATE_PATH
    deploy_namespace = mock_deploy.call_args[0][0]
    assert deploy_namespace.stack_name == EXPECTED_STACK_NAME


def test_no_changes_package_handler(packager, caplog):
    changeset_empty = ChangeEmptyError(stack_name=EXPECTED_STACK_NAME)

    package = patch.object(PackageCommand, "_run_main", return_value=None)
    deploy = patch.object(DeployCommand, "_run_main", side_effect=changeset_empty)
    output = patch.object(
        Packager,
        "get_stack_outputs",
        return_value={HANDLER_ARN_KEY: EXPECTED_HANDLER_ARN},
    )
    caplog.set_level(logging.INFO)

    with package as mock_package, deploy as mock_deploy, output as mock_output:
        packager.package_handler(
            EXPECTED_BUCKET, EXPECTED_TEMPLATE_PATH, EXPECTED_STACK_NAME, {}
        )

    mock_output.assert_called_once()
    mock_package.assert_called_once()
    mock_deploy.assert_called_once()

    assert any("No changes to deploy." in record.message for record in caplog.records)


def test_get_stack_outputs(packager):
    stubber = Stubber(packager.client)
    response = {
        "Stacks": [
            {
                "StackName": EXPECTED_STACK_NAME,
                "Outputs": [{"OutputKey": OUTPUT_KEY, "OutputValue": OUTPUT_VALUE}],
                "StackStatus": "CREATE_COMPLETE",
                "CreationTime": FAKE_DATETIME,
            }
        ]
    }
    stubber.add_response("describe_stacks", response)
    with stubber:
        returned_outputs = packager.get_stack_outputs(EXPECTED_STACK_NAME)
    assert returned_outputs[OUTPUT_KEY] == OUTPUT_VALUE
    stubber.assert_no_pending_responses()


def test_get_output():
    outputs = {OUTPUT_KEY: OUTPUT_VALUE}
    ret_value = Packager.get_output(outputs, OUTPUT_KEY, EXPECTED_STACK_NAME)
    assert ret_value == OUTPUT_VALUE


def test_no_output_get_stack_output():
    outputs = {}
    with pytest.raises(OutputNotFoundError):
        Packager.get_output(outputs, OUTPUT_KEY, EXPECTED_STACK_NAME)


def test_package(packager):
    create_update_patch = patch.object(Packager, "create_or_update_stack")
    expected_out = "ExpectedOut"

    expected_outputs = {param: expected_out for param in HANDLER_PARAMS}
    expected_outputs["BucketName"] = expected_out
    stack_output_patch = patch.object(
        Packager, "get_stack_outputs", return_value=expected_outputs
    )
    package_patch = patch.object(Packager, "package_handler")

    with create_update_patch as mock_create_update, (
        stack_output_patch
    ) as mock_stack_output, package_patch as mock_package:
        packager.package("stackName", {})

    raw_template = pkg_resources.resource_string(
        "rpdk", "data/CloudFormationHandlerInfrastructure.yaml"
    )
    mock_create_update.assert_called_once_with(
        INFRA_STACK_NAME, raw_template.decode("utf-8")
    )

    mock_stack_output.assert_called_once()
    expected_handler_params = {
        "EncryptionKey": expected_out,
        "LambdaRole": expected_out,
    }
    mock_package.assert_called_with(
        expected_out, HANDLER_TEMPLATE_PATH, "stackName", expected_handler_params
    )
