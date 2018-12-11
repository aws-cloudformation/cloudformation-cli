import logging
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from tempfile import NamedTemporaryFile

import botocore.exceptions
from awscli.customizations.cloudformation.deploy import DeployCommand
from awscli.customizations.cloudformation.exceptions import ChangeEmptyError
from awscli.customizations.cloudformation.package import PackageCommand
from botocore.session import Session

LOG = logging.getLogger(__name__)


class OutputNotFoundError(Exception):
    def __init__(self, stack_name, key):
        message = "Output with key '{}' not found in stack '{}'".format(key, stack_name)
        super().__init__(message)


NO_UPDATES_ERROR_MESSAGE = "No updates are to be performed."
SHARED_ARGS = {"s3_prefix": None, "kms_key_id": None, "force_upload": False}
CAPABILITIES = ["CAPABILITY_IAM", "CAPABILITY_AUTO_EXPAND"]


def create_or_update_stack(client, stack_name, template_body):
    args = {
        "StackName": stack_name,
        "TemplateBody": template_body,
        "Capabilities": CAPABILITIES,
    }
    try:
        LOG.info("Creating stack '%s'", stack_name)
        client.create_stack(**args)
    except client.exceptions.AlreadyExistsException:
        LOG.info("Stack '%s' already exists. Attempting to update stack", stack_name)
        try:
            client.update_stack(**args)
        except botocore.exceptions.ClientError as e:
            msg = str(e)
            if NO_UPDATES_ERROR_MESSAGE in msg:
                LOG.info("No updates to be performed for stack '%s'", stack_name)
            else:
                raise
        else:
            stack_wait(client, stack_name, "stack_update_complete")
            LOG.info("Stack '%s' successfully updated", stack_name)
    else:
        stack_wait(client, stack_name, "stack_create_complete")
        LOG.info("Stack '%s' successfully created", stack_name)


def stack_wait(client, stack_name, terminal_state):
    waiter = client.get_waiter(terminal_state)
    waiter.wait(StackName=stack_name, WaiterConfig={"Delay": 5, "MaxAttempts": 200})


def package_handler(
    bucket_name, template_file, stack_name
):  # pylint: disable=protected-access
    session = Session()
    package_args = {
        "template_file": template_file,
        "s3_bucket": bucket_name,
        "metadata": None,
        "use_json": False,
    }
    package_args.update(SHARED_ARGS)

    deploy_args = {
        "stack_name": stack_name,
        "s3_bucket": None,
        "parameter_overrides": [],
        "tags": [],
        "execute_changeset": True,
        "role_arn": None,
        "notification_arns": [],
        "fail_on_empty_changeset": True,
        "capabilities": CAPABILITIES,
    }
    deploy_args.update(SHARED_ARGS)

    global_ns = Namespace(
        region=session.get_config_variable("region"), verify_ssl=True, endpoint_url=None
    )
    package_command = PackageCommand(session)
    deploy_command = DeployCommand(session)
    captured_out = StringIO()
    with NamedTemporaryFile() as output_file, redirect_stdout(captured_out):
        package_ns = Namespace(**package_args, output_template_file=output_file.name)
        LOG.info("Packaging local file specified in '%s'", template_file)
        package_command._run_main(package_ns, global_ns)
        LOG.info("Packaging successful. Now creating handler stack '%s'", stack_name)
        deploy_ns = Namespace(**deploy_args, template_file=output_file.name)
        try:
            deploy_command._run_main(deploy_ns, global_ns)
        except ChangeEmptyError as e:
            LOG.info(str(e))
        else:
            LOG.info(
                "Successfully deployed handler stack '%s' from SAM template '%s'",
                stack_name,
                template_file,
            )


def get_stack_output(client, stack_name, output_key):
    result = client.describe_stacks(StackName=stack_name)
    outputs = result["Stacks"][0]["Outputs"]
    for output in outputs:
        if output["OutputKey"] == output_key:
            return output["OutputValue"]
    raise OutputNotFoundError(stack_name, output_key)
