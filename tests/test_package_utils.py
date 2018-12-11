# pylint: disable=redefined-outer-name
import datetime
import logging
from unittest.mock import patch

import boto3
import botocore.exceptions
import pytest
from awscli.customizations.cloudformation.deploy import DeployCommand
from awscli.customizations.cloudformation.exceptions import ChangeEmptyError
from awscli.customizations.cloudformation.package import PackageCommand
from botocore.stub import ANY, Stubber
from dateutil.tz import tzutc

from rpdk.package_utils import (
    OutputNotFoundError,
    create_or_update_stack,
    get_stack_output,
    package_handler,
    stack_wait,
)

EXPECTED_STACK_PARAMS = {
    "StackName": "Stack",
    "TemplateBody": "Body",
    "Capabilities": ANY,
}


@pytest.fixture
def cfn_client():
    return boto3.client("cloudformation")


def test_create_stack_success(cfn_client):
    stubber = Stubber(cfn_client)
    stubber.add_response("create_stack", {}, EXPECTED_STACK_PARAMS)
    wait_patch = patch("rpdk.package_utils.stack_wait", autospec=True)
    with stubber, wait_patch:
        create_or_update_stack(
            cfn_client,
            EXPECTED_STACK_PARAMS["StackName"],
            EXPECTED_STACK_PARAMS["TemplateBody"],
        )


def test_create_already_exists_update_success(cfn_client):
    stubber = Stubber(cfn_client)

    stubber.add_client_error("create_stack", "AlreadyExistsException")
    stubber.add_response("update_stack", {}, EXPECTED_STACK_PARAMS)
    wait_patch = patch("rpdk.package_utils.stack_wait", autospec=True)
    with stubber, wait_patch:
        create_or_update_stack(
            cfn_client,
            EXPECTED_STACK_PARAMS["StackName"],
            EXPECTED_STACK_PARAMS["TemplateBody"],
        )


def test_create_exists_update_noop(cfn_client):
    stubber = Stubber(cfn_client)
    stubber.add_client_error("create_stack", "AlreadyExistsException")
    stubber.add_client_error(
        "update_stack",
        "ClientError",
        "An error occurred (ValidationError) when calling the UpdateStack"
        " operation: No updates are to be performed.",
    )
    wait_patch = patch("rpdk.package_utils.stack_wait", autospec=True)
    with stubber, wait_patch:
        create_or_update_stack(
            cfn_client,
            EXPECTED_STACK_PARAMS["StackName"],
            EXPECTED_STACK_PARAMS["TemplateBody"],
        )


def test_create_exists_update_fails(cfn_client):
    stubber = Stubber(cfn_client)
    stubber.add_client_error("create_stack", "AlreadyExistsException")
    stubber.add_client_error("update_stack", "ClientError")
    wait_patch = patch("rpdk.package_utils.stack_wait", autospec=True)
    with stubber, wait_patch, pytest.raises(botocore.exceptions.ClientError):
        create_or_update_stack(
            cfn_client,
            EXPECTED_STACK_PARAMS["StackName"],
            EXPECTED_STACK_PARAMS["TemplateBody"],
        )


def test_stack_wait(cfn_client):
    stubber = Stubber(cfn_client)
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
        stack_wait(
            cfn_client, EXPECTED_STACK_PARAMS["StackName"], "stack_create_complete"
        )


def test_package_handler():
    expected_bucket = "MyBucket"
    expected_template_file = "template_file.path"
    package_patch = patch.object(PackageCommand, "_run_main", return_value=None)
    deploy_patch = patch.object(DeployCommand, "_run_main", return_value=None)
    with package_patch as mock_package, deploy_patch as mock_deploy:
        package_handler(
            expected_bucket, expected_template_file, EXPECTED_STACK_PARAMS["StackName"]
        )
    mock_package.assert_called_once()
    mock_deploy.assert_called_once()

    package_namespace = mock_package.call_args[0][0]
    assert package_namespace.s3_bucket == expected_bucket
    assert package_namespace.template_file == expected_template_file
    deploy_namespace = mock_deploy.call_args[0][0]
    assert deploy_namespace.stack_name == EXPECTED_STACK_PARAMS["StackName"]


def test_package_handler_no_changes(caplog):
    expected_bucket = "MyBucket"
    expected_template_file = "template_file.path"

    package_patch = patch.object(PackageCommand, "_run_main", return_value=None)
    changeset_empty = ChangeEmptyError(stack_name=EXPECTED_STACK_PARAMS["StackName"])
    deploy_patch = patch.object(DeployCommand, "_run_main", side_effect=changeset_empty)
    caplog.set_level(logging.INFO)
    with package_patch as mock_package, deploy_patch as mock_deploy:
        package_handler(
            expected_bucket, expected_template_file, EXPECTED_STACK_PARAMS["StackName"]
        )
    mock_package.assert_called_once()
    mock_deploy.assert_called_once()

    last_record = caplog.records[-1]
    assert "No changes to deploy." in last_record.message


def test_get_stack_output(cfn_client):
    stubber = Stubber(cfn_client)
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
        returned_output = get_stack_output(
            cfn_client, EXPECTED_STACK_PARAMS["StackName"], "MyKey"
        )
    assert returned_output == output_value


def test_get_stack_output_none(cfn_client):
    stubber = Stubber(cfn_client)
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
    with stubber, pytest.raises(OutputNotFoundError):
        get_stack_output(cfn_client, EXPECTED_STACK_PARAMS["StackName"], "MyKy")
