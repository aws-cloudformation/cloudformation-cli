import logging
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from tempfile import NamedTemporaryFile

import botocore.exceptions
import pkg_resources
from awscli.customizations.cloudformation.deploy import DeployCommand
from awscli.customizations.cloudformation.exceptions import ChangeEmptyError
from awscli.customizations.cloudformation.package import PackageCommand
from botocore.session import Session

LOG = logging.getLogger(__name__)


class OutputNotFoundError(Exception):
    def __init__(self, stack_name, key):
        message = "Output with key '{}' not found in stack '{}'".format(key, stack_name)
        super().__init__(message)


NO_UPDATES_ERROR_MESSAGE = "No updates are to be performed"
SHARED_ARGS = {"s3_prefix": None, "kms_key_id": None, "force_upload": False}
CAPABILITIES = ("CAPABILITY_IAM", "CAPABILITY_AUTO_EXPAND")
INFRA_TEMPLATE_PATH = "data/CloudFormationHandlerInfrastructure.yaml"
INFRA_STACK_NAME = "CFNResourceHandlerInfrastructure"
INFRA_BUCKET_NAME = "BucketName"
INFRA_ROLE = "LambdaRole"
INFRA_KEY = "EncryptionKey"
HANDLER_PARAMS = (INFRA_KEY, INFRA_ROLE)
HANDLER_TEMPLATE_PATH = "./Handler.yaml"
HANDLER_ARN_KEY = "ResourceHandlerArn"


class Packager:
    def __init__(self, client):
        self.client = client

    def package(self, handler_stack_name, handler_params):
        raw_infra_template = pkg_resources.resource_string(
            __name__, INFRA_TEMPLATE_PATH
        )
        decoded_template = raw_infra_template.decode("utf-8")
        self.create_or_update_stack(INFRA_STACK_NAME, decoded_template)
        outputs = self.get_stack_outputs(INFRA_STACK_NAME)
        bucket_name = self.get_output(outputs, INFRA_BUCKET_NAME, INFRA_STACK_NAME)
        output_params = {
            param: self.get_output(outputs, param, INFRA_STACK_NAME)
            for param in HANDLER_PARAMS
        }

        handler_params.update(output_params)
        return self.package_handler(
            bucket_name, HANDLER_TEMPLATE_PATH, handler_stack_name, handler_params
        )

    def create_or_update_stack(self, stack_name, template_body):
        args = {
            "StackName": stack_name,
            "TemplateBody": template_body,
            "Capabilities": CAPABILITIES,
        }
        # attempt to create stack. if the stack already exists, try to update it
        try:
            LOG.info("Creating stack '%s'", stack_name)
            self.client.create_stack(**args)
        except self.client.exceptions.AlreadyExistsException:
            LOG.info(
                "Stack '%s' already exists. Attempting to update stack", stack_name
            )
            try:
                self.client.update_stack(**args)
            except botocore.exceptions.ClientError as e:
                # if the update is a noop, don't do anything else
                msg = str(e)
                if NO_UPDATES_ERROR_MESSAGE in msg:
                    LOG.info("%s for stack '%s'", NO_UPDATES_ERROR_MESSAGE, stack_name)
                else:
                    raise
            else:
                self.stack_wait(stack_name, "stack_update_complete")
                LOG.info("Stack '%s' successfully updated", stack_name)
        else:
            self.stack_wait(stack_name, "stack_create_complete")
            LOG.info("Stack '%s' successfully created", stack_name)
            self.client.update_termination_protection(
                EnableTerminationProtection=True, StackName=stack_name
            )

    def stack_wait(self, stack_name, terminal_state):
        # waits for stack with name stack_name to be in state terminal_state
        waiter = self.client.get_waiter(terminal_state)
        waiter.wait(StackName=stack_name, WaiterConfig={"Delay": 5, "MaxAttempts": 200})

    def get_stack_outputs(self, stack_name):
        result = self.client.describe_stacks(StackName=stack_name)
        outputs = result["Stacks"][0]["Outputs"]
        return {output["OutputKey"]: output["OutputValue"] for output in outputs}

    @staticmethod
    def get_output(outputs, key, stack_name):
        try:
            return outputs[key]
        except KeyError:
            raise OutputNotFoundError(stack_name, key)

    def package_handler(
        self, bucket_name, template_file, stack_name, params
    ):  # pylint: disable=protected-access,too-many-locals
        session = Session()

        # setting up argument namespaces for the package command
        package_args = {
            "template_file": template_file,
            "s3_bucket": bucket_name,
            "metadata": None,
            "use_json": False,
        }
        package_args.update(SHARED_ARGS)
        # preparing arguments for package
        # convert parameters into correct format
        formatted_params = ["{}={}".format(key, value) for key, value in params.items()]

        deploy_args = {
            "stack_name": stack_name,
            "s3_bucket": None,
            "parameter_overrides": formatted_params,
            "tags": [],
            "execute_changeset": True,
            "role_arn": None,
            "notification_arns": [],
            "fail_on_empty_changeset": True,
            "capabilities": CAPABILITIES,
        }
        deploy_args.update(SHARED_ARGS)

        # global namespace for the commands that includes information like region
        global_ns = Namespace(
            region=session.get_config_variable("region"),
            verify_ssl=True,
            endpoint_url=None,
        )

        captured_out = StringIO()
        with NamedTemporaryFile() as output_file, redirect_stdout(captured_out):
            # adding temporary file to namespace for the output template
            package_ns = Namespace(
                **package_args, output_template_file=output_file.name
            )
            LOG.info(
                "Uploading local code package to bucket '%s' "
                "and outputting modified template",
                bucket_name,
            )
            # uploads file to s3 and outputs modified template with s3 location
            PackageCommand(session)._run_main(package_ns, global_ns)
            LOG.info("Upload successful. Now deploying handler stack '%s'", stack_name)
            # adds output file to deploy arguments
            deploy_ns = Namespace(**deploy_args, template_file=output_file.name)
            try:
                # deploys stack, which creates stack changeset
                # from rewritten template and executes it
                DeployCommand(session)._run_main(deploy_ns, global_ns)
            except ChangeEmptyError as e:
                # If there are no changes between templates,
                # log that and still return the handler arn
                LOG.info(str(e))
            else:
                LOG.info("Successfully deployed handler stack '%s'", stack_name)
        outputs = self.get_stack_outputs(stack_name)
        handler_arn = self.get_output(outputs, HANDLER_ARN_KEY, stack_name)
        LOG.info("Lambda function handler: '%s'", handler_arn)
        captured_out.close()
        return handler_arn
