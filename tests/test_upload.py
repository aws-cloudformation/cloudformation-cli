# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,useless-super-delegation,protected-access
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import ANY, Mock, patch
from urllib.parse import urlsplit

import pytest
from botocore.exceptions import ClientError, WaiterError

from rpdk.core.exceptions import (
    DownstreamError,
    InternalError,
    InvalidProjectError,
    UploadError,
)
from rpdk.core.upload import (
    BUCKET_OUTPUT_NAME,
    EXECUTION_ROLE_ARN_OUTPUT_NAME,
    INFRA_STACK_NAME,
    LOG_DELIVERY_ROLE_ARN_OUTPUT_NAME,
    Uploader,
)

from .utils import CONTENTS_UTF8

BUCKET_OUTPUT_VALUE = "cloudformationmanageduploadinfrast-artifactbucket-154zq5ecxpp2u"
LOG_DELIVERY_ROLE_ARN_OUTPUT_VALUE = "arn:aws:iam::123456789012:role/CloudFormationManagedUplo-LogAndMetricsDeliveryRol-7HGNMUOAABC1"  # noqa: B950 as it conflicts with formatting rules # pylint: disable=C0301
STACK_ID = (
    "arn:aws:cloudformation:us-east-1:xxxxxxxxxxxx:stack/"
    + INFRA_STACK_NAME
    + "/f2af5ac0-615a-11e9-b390-0e1ffe4de6a4"
)
BLANK_CLIENT_ERROR = {"Error": {"Code": "", "Message": ""}}


def describe_stacks_result(outputs):
    return {
        "Stacks": [
            {
                "StackId": STACK_ID,
                "StackName": INFRA_STACK_NAME,
                "Description": (
                    "This CloudFormation template provisions all the "
                    "infrastructure that is required to upload artifacts to "
                    "CloudFormation's managed experience.\n"
                ),
                "CreationTime": "2019-04-17T21:51:25.923Z",
                "RollbackConfiguration": {"RollbackTriggers": []},
                "StackStatus": "CREATE_COMPLETE",
                "DisableRollback": False,
                "NotificationARNs": [],
                "Outputs": outputs,
                "Tags": [],
                "EnableTerminationProtection": True,
                "DriftInformation": {"StackDriftStatus": "NOT_CHECKED"},
            }
        ]
    }


class AlreadyExistsException(Exception):
    pass


@pytest.fixture
def uploader():
    uploader = Uploader(Mock(), Mock())
    uploader.cfn_client.exceptions.AlreadyExistsException = AlreadyExistsException
    return uploader


def test__get_template_output_name_mismatched(uploader):
    with patch(
        "rpdk.core.upload.resource_stream", return_value=StringIO("")
    ) as mock_stream:
        with pytest.raises(InternalError):
            uploader._get_template()

    mock_stream.assert_called_once_with(
        "rpdk.core.upload", "data/managed-upload-infrastructure.yaml"
    )


def test__wait_for_stack_failure(uploader):
    e = WaiterError(
        name="StackCreateComplete",
        reason="Waiter encountered a terminal failure state",
        last_response=None,
    )
    mock_waiter = uploader.cfn_client.get_waiter.return_value
    mock_waiter.wait.side_effect = e

    with pytest.raises(UploadError) as excinfo:
        uploader._wait_for_stack("stack-foo", "StackCreateComplete", "success-msg")

    mock_waiter.wait.assert_called_once_with(StackName="stack-foo", WaiterConfig=ANY)
    assert excinfo.value.__cause__ is e


def test__wait_for_stack_success(uploader):
    mock_waiter = uploader.cfn_client.get_waiter.return_value
    uploader._wait_for_stack("stack-foo", "waiter-name", "success-msg")
    mock_waiter.wait.assert_called_once_with(StackName="stack-foo", WaiterConfig=ANY)


def test__get_stack_output_output_found(uploader):
    uploader.cfn_client.describe_stacks.return_value = describe_stacks_result(
        [{"OutputKey": "foo", "OutputValue": "bar"}]
    )
    bucket_name = uploader._get_stack_output("stack-foo", "foo")
    assert bucket_name == "bar"


def test__get_stack_output_output_not_found_empty(uploader):
    uploader.cfn_client.describe_stacks.return_value = describe_stacks_result([])
    with pytest.raises(InternalError):
        uploader._get_stack_output("stack-foo", "foo")


def test__get_stack_output_output_not_found_wrong_key(uploader):
    uploader.cfn_client.describe_stacks.return_value = describe_stacks_result(
        [{"OutputKey": "fuz", "OutputValue": "bar"}]
    )
    with pytest.raises(InternalError):
        uploader._get_stack_output("stack-foo", "foo")


def test_upload_s3_clienterror(uploader):
    fileobj = object()
    uploader.cfn_client.describe_stacks.return_value = describe_stacks_result(
        [
            {"OutputKey": BUCKET_OUTPUT_NAME, "OutputValue": BUCKET_OUTPUT_VALUE},
            {
                "OutputKey": LOG_DELIVERY_ROLE_ARN_OUTPUT_NAME,
                "OutputValue": LOG_DELIVERY_ROLE_ARN_OUTPUT_VALUE,
            },
        ]
    )
    patch_stack = patch.object(
        uploader, "_create_or_update_stack", return_value="stack-foo"
    )
    uploader.s3_client.upload_fileobj.side_effect = ClientError(
        BLANK_CLIENT_ERROR, "upload_fileobj"
    )

    with patch_stack as mock_stack:
        with pytest.raises(DownstreamError):
            uploader.upload("foo", fileobj)

    mock_stack.assert_called_once_with(ANY, INFRA_STACK_NAME)
    uploader.s3_client.upload_fileobj.assert_called_once_with(
        fileobj, BUCKET_OUTPUT_VALUE, ANY
    )


def test_upload_s3_success(uploader):
    fileobj = object()
    uploader.cfn_client.describe_stacks.return_value = describe_stacks_result(
        [
            {"OutputKey": BUCKET_OUTPUT_NAME, "OutputValue": BUCKET_OUTPUT_VALUE},
            {
                "OutputKey": LOG_DELIVERY_ROLE_ARN_OUTPUT_NAME,
                "OutputValue": LOG_DELIVERY_ROLE_ARN_OUTPUT_VALUE,
            },
        ]
    )
    patch_stack = patch.object(
        uploader, "_create_or_update_stack", return_value="stack-foo"
    )
    patch_time = patch("rpdk.core.upload.datetime", autospec=True)

    with patch_stack as mock_stack, patch_time as mock_time:
        mock_time.utcnow.return_value = datetime(2004, 11, 17, 20, 54, 33)
        s3_url = uploader.upload(CONTENTS_UTF8, fileobj)

    mock_stack.assert_called_once_with(ANY, INFRA_STACK_NAME)
    mock_time.utcnow.assert_called_once_with()
    expected_key = "{}-2004-11-17T20-54-33.zip".format(CONTENTS_UTF8)
    uploader.s3_client.upload_fileobj.assert_called_once_with(
        fileobj, BUCKET_OUTPUT_VALUE, expected_key
    )

    assert uploader.get_log_delivery_role_arn() == LOG_DELIVERY_ROLE_ARN_OUTPUT_VALUE

    result = urlsplit(s3_url)

    assert result.query == ""
    assert result.fragment == ""
    assert result.scheme == "s3"
    assert result.netloc == BUCKET_OUTPUT_VALUE
    key = result.path.lstrip("/")
    assert key == expected_key


def test__create_or_update_stack_stack_doesnt_exist(uploader):
    uploader.cfn_client.create_stack.return_value = {"StackId": STACK_ID}
    with patch.object(uploader, "_wait_for_stack", autospec=True) as mock_wait:
        stack_id = uploader._create_or_update_stack(CONTENTS_UTF8, INFRA_STACK_NAME)

    assert stack_id == STACK_ID

    uploader.cfn_client.create_stack.assert_called_once_with(
        Capabilities=["CAPABILITY_IAM"],
        StackName=INFRA_STACK_NAME,
        TemplateBody=CONTENTS_UTF8,
        EnableTerminationProtection=True,
    )
    mock_wait.assert_called_once_with(STACK_ID, "stack_create_complete", ANY)


def test__create_or_update_stack_stack_exists_and_no_changes(uploader):
    class AlreadyExistsException(Exception):
        pass

    uploader.cfn_client.exceptions.AlreadyExistsException = AlreadyExistsException
    uploader.cfn_client.create_stack.side_effect = AlreadyExistsException
    uploader.cfn_client.update_stack.side_effect = ClientError(
        {"Error": {"Code": "", "Message": "No updates are to be performed"}},
        "update_stack",
    )

    with patch.object(uploader, "_wait_for_stack", autospec=True) as mock_wait:
        stack_id = uploader._create_or_update_stack(CONTENTS_UTF8, INFRA_STACK_NAME)

    assert stack_id == INFRA_STACK_NAME

    uploader.cfn_client.create_stack.assert_called_once_with(
        Capabilities=["CAPABILITY_IAM"],
        StackName=INFRA_STACK_NAME,
        TemplateBody=CONTENTS_UTF8,
        EnableTerminationProtection=True,
    )
    uploader.cfn_client.update_stack.assert_called_once_with(
        Capabilities=["CAPABILITY_IAM"],
        StackName=INFRA_STACK_NAME,
        TemplateBody=CONTENTS_UTF8,
    )

    mock_wait.assert_not_called()


def test__create_or_update_stack_stack_exists_and_needs_changes(uploader):
    uploader.cfn_client.create_stack.side_effect = AlreadyExistsException
    uploader.cfn_client.update_stack.return_value = {"StackId": STACK_ID}

    with patch.object(uploader, "_wait_for_stack", autospec=True) as mock_wait:
        stack_id = uploader._create_or_update_stack(CONTENTS_UTF8, INFRA_STACK_NAME)

    assert stack_id == STACK_ID

    uploader.cfn_client.create_stack.assert_called_once_with(
        Capabilities=["CAPABILITY_IAM"],
        StackName=INFRA_STACK_NAME,
        TemplateBody=CONTENTS_UTF8,
        EnableTerminationProtection=True,
    )
    uploader.cfn_client.update_stack.assert_called_once_with(
        Capabilities=["CAPABILITY_IAM"],
        StackName=INFRA_STACK_NAME,
        TemplateBody=CONTENTS_UTF8,
    )

    mock_wait.assert_called_once_with(STACK_ID, "stack_update_complete", ANY)


def test__create_or_update_stack_create_unknown_failure(uploader):
    uploader.cfn_client.create_stack.side_effect = ClientError(
        BLANK_CLIENT_ERROR, "create_stack"
    )

    with patch.object(uploader, "_wait_for_stack", autospec=True) as mock_wait:
        with pytest.raises(DownstreamError):
            uploader._create_or_update_stack(CONTENTS_UTF8, INFRA_STACK_NAME)

    uploader.cfn_client.create_stack.assert_called_once_with(
        Capabilities=["CAPABILITY_IAM"],
        StackName=INFRA_STACK_NAME,
        TemplateBody=CONTENTS_UTF8,
        EnableTerminationProtection=True,
    )

    assert uploader.get_log_delivery_role_arn() == ""

    mock_wait.assert_not_called()


def test__create_or_update_stack_update_unknown_failure(uploader):
    uploader.cfn_client.create_stack.side_effect = AlreadyExistsException
    uploader.cfn_client.update_stack.side_effect = ClientError(
        BLANK_CLIENT_ERROR, "update_stack"
    )

    with patch.object(uploader, "_wait_for_stack", autospec=True) as mock_wait:
        with pytest.raises(DownstreamError):
            uploader._create_or_update_stack(CONTENTS_UTF8, INFRA_STACK_NAME)

    uploader.cfn_client.create_stack.assert_called_once_with(
        Capabilities=["CAPABILITY_IAM"],
        StackName=INFRA_STACK_NAME,
        TemplateBody=CONTENTS_UTF8,
        EnableTerminationProtection=True,
    )
    uploader.cfn_client.update_stack.assert_called_once_with(
        Capabilities=["CAPABILITY_IAM"],
        StackName=INFRA_STACK_NAME,
        TemplateBody=CONTENTS_UTF8,
    )

    mock_wait.assert_not_called()


def test_create_or_update_role(uploader):
    uploader.cfn_client.create_stack.return_value = {"StackId": STACK_ID}
    uploader.cfn_client.describe_stacks.return_value = describe_stacks_result(
        [{"OutputKey": EXECUTION_ROLE_ARN_OUTPUT_NAME, "OutputValue": "bar"}]
    )
    file_path = Path()
    with patch.object(Path, "open", return_value=StringIO("template")):
        uploader.create_or_update_role(file_path, "my-resource-type")


def test_create_or_update_role_not_found(uploader):
    file_path = Path()
    with patch.object(Path, "open", side_effect=FileNotFoundError), pytest.raises(
        InvalidProjectError
    ):
        uploader.create_or_update_role(file_path, "my-resource-type")
