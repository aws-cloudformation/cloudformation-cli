# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import logging
from contextlib import contextmanager
from unittest.mock import Mock

import boto3
import pytest

from rpdk.packager import Packager

from .utils import random_name

LOG = logging.getLogger(__name__)

DUMMY_TEMPLATE = """Resources:
  {}:
    Type: AWS::CloudFormation::WaitConditionHandle
"""


@pytest.fixture
def client():
    return boto3.client("cloudformation")


@contextmanager
def cleanup_stack(client, stack_name):
    try:
        yield
    finally:
        try:
            client.update_termination_protection(
                StackName=stack_name, EnableTerminationProtection=False
            )
        except Exception as e:  # pylint: disable=broad-except
            LOG.warning(str(e))
        try:
            client.delete_stack(StackName=stack_name)
        except Exception as e:  # pylint: disable=broad-except
            LOG.warning(str(e))
        # since we are using random stack names, don't wait for cleanup


def test_cleanup_stack_exception_in_with_statement():
    stack_name = random_name()
    mock_client = Mock()

    with pytest.raises(ValueError):  # don't swallow error
        with cleanup_stack(mock_client, stack_name):
            raise ValueError()

    mock_client.update_termination_protection.assert_called_once_with(
        StackName=stack_name, EnableTerminationProtection=False
    )
    mock_client.delete_stack.assert_called_once_with(StackName=stack_name)


def test_cleanup_stack_exception_update_termination_protection():
    stack_name = random_name()
    mock_client = Mock()

    mock_client.update_termination_protection.side_effect = Exception()

    with cleanup_stack(mock_client, stack_name):
        pass

    mock_client.update_termination_protection.assert_called_once_with(
        StackName=stack_name, EnableTerminationProtection=False
    )
    mock_client.delete_stack.assert_called_once_with(StackName=stack_name)


def test_cleanup_stack_exception_delete_stack():
    stack_name = random_name()
    mock_client = Mock()

    mock_client.delete_stack.side_effect = Exception()

    with cleanup_stack(mock_client, stack_name):
        pass

    mock_client.update_termination_protection.assert_called_once_with(
        StackName=stack_name, EnableTerminationProtection=False
    )
    mock_client.delete_stack.assert_called_once_with(StackName=stack_name)


# by parametrizing the randomly generated stack name, it will be printed on failure
@pytest.mark.parametrize("stack_name", [random_name()])
def test_create_or_update_stack_create(client, stack_name):
    packager = Packager(client)
    template = DUMMY_TEMPLATE.format("NullResource")

    with cleanup_stack(client, stack_name):
        packager.create_or_update_stack(stack_name, template)
        result = client.describe_stacks(StackName=stack_name)

    assert len(result["Stacks"]) == 1
    stack = result["Stacks"][0]
    assert stack["StackStatus"] == "CREATE_COMPLETE"
    assert stack["EnableTerminationProtection"] is True


# by parametrizing the randomly generated stack name, it will be printed on failure
@pytest.mark.parametrize("stack_name", [random_name()])
def test_create_or_update_stack_update_noop(client, stack_name):
    packager = Packager(client)
    template = DUMMY_TEMPLATE.format("NullResource")

    with cleanup_stack(client, stack_name):
        packager.create_or_update_stack(stack_name, template)
        packager.create_or_update_stack(stack_name, template)
        result = client.describe_stacks(StackName=stack_name)

    assert len(result["Stacks"]) == 1
    stack = result["Stacks"][0]
    assert stack["StackStatus"] == "CREATE_COMPLETE"
    assert stack["EnableTerminationProtection"] is True


# by parametrizing the randomly generated stack name, it will be printed on failure
@pytest.mark.parametrize("stack_name", [random_name()])
def test_create_or_update_stack_update_changed(client, stack_name):
    packager = Packager(client)
    template_one = DUMMY_TEMPLATE.format("OneResource")
    template_two = DUMMY_TEMPLATE.format("TwoResource")

    with cleanup_stack(client, stack_name):
        packager.create_or_update_stack(stack_name, template_one)
        packager.create_or_update_stack(stack_name, template_two)
        result = client.describe_stacks(StackName=stack_name)

    assert len(result["Stacks"]) == 1
    stack = result["Stacks"][0]
    assert stack["StackStatus"] == "UPDATE_COMPLETE"
    assert stack["EnableTerminationProtection"] is True
