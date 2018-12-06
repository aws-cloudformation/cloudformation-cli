# pylint: disable=useless-super-delegation,too-many-locals
# pylint doesn't recognize abstract methods
import json
import logging
import shutil

<<<<<<< HEAD
=======
import boto3
import botocore.exceptions

from rpdk.data_loaders import copy_resource, resource_yaml
from rpdk.filters import resource_type_resource
>>>>>>> Package command for java lambdas
from rpdk.jsonutils.flattener import JsonSchemaFlattener
from rpdk.plugin_base import LanguagePlugin

from .pojo_resolver import JavaPojoResolver
from .utils import safe_reserved

LOG = logging.getLogger(__name__)

OPERATIONS = ("Create", "Read", "Update", "Delete", "List")
EXECUTABLE = "uluru-cli"


class JavaLanguagePlugin(LanguagePlugin):
    MODULE_NAME = __name__
    NAME = "java"
    INFRA_STACK = "CFNResourceHandlerInfrastructure"
    HANDLER_STACK = "ResourceHandlerStack"

    def __init__(self):
        self.env = self._setup_jinja_env(
            trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True
        )
        self.namespace = None
        self.package_name = None

    def _namespace_from_project(self, project):
        self.namespace = ("com",) + tuple(
            safe_reserved(s.lower()) for s in project.type_info
        )
        self.package_name = ".".join(self.namespace)


    def init(self, project):
        LOG.debug("Init started")

        self._namespace_from_project(project)

        # maven folder structure
        src = (project.root / "src" / "main" / "java").joinpath(*self.namespace)
        LOG.debug("Making source folder structure: %s", src)
        src.mkdir(parents=True, exist_ok=True)
        tst = (project.root / "src" / "test" / "java").joinpath(*self.namespace)
        LOG.debug("Making test folder structure: %s", tst)
        tst.mkdir(parents=True, exist_ok=True)

        path = project.root / "pom.xml"
        LOG.debug("Writing Maven POM: %s", path)
        template = self.env.get_template("pom.xml")
        contents = template.render(
            group_id=self.package_name, artifact_id="foo", executable=EXECUTABLE
        )
        project.safewrite(path, contents)

        LOG.debug("Writing stub handlers")
        template = self.env.get_template("StubHandler.java")

        for operation in OPERATIONS:
            path = src / "{}Handler.java".format(operation)
            LOG.debug("%s handler: %s", operation, path)
            contents = template.render(
                package_name=self.package_name,
                operation=operation,
                pojo_name="ResourceModel",
            )
            project.safewrite(path, contents)

        path = project.root / "README.md"
        LOG.debug("Writing README: %s", path)
        template = self.env.get_template("README.md")
        contents = template.render(
            type_name=project.type_name,
            schema_path=project.schema_path,
            executable=EXECUTABLE,
        )
        project.safewrite(path, contents)

        LOG.debug("Init complete")

    @staticmethod
    def _get_generated_root(project):
        return project.root / "target" / "generated-sources" / "rpdk"

    def generate(self, project):
        LOG.debug("Generate started")

        self._namespace_from_project(project)

        objects = JsonSchemaFlattener(project.schema).flatten_schema()

        generated_root = self._get_generated_root(project)
        LOG.debug("Removing generated sources: %s", generated_root)
        shutil.rmtree(generated_root, ignore_errors=True)

        src = generated_root.joinpath(*self.namespace)
        LOG.debug("Making generated folder structure: %s", src)
        src.mkdir(parents=True, exist_ok=True)

        path = src / "BaseHandler.java"
        LOG.debug("Writing base handler: %s", path)
        template = self.env.get_template("BaseHandler.java")
        contents = template.render(
            package_name=self.package_name,
            operations=OPERATIONS,
            pojo_name="ResourceModel",
        )
        project.overwrite(path, contents)

        pojo_resolver = JavaPojoResolver(objects, "ResourceModel")
        pojos = pojo_resolver.resolve_pojos()

        LOG.debug("Writing %d POJOs", len(pojos))

        template = self.env.get_template("POJO.java")
        for pojo_name, properties in pojos.items():
            path = src / "{}.java".format(pojo_name)
            LOG.debug("%s POJO: %s", pojo_name, path)
            contents = template.render(
                package_name=self.package_name,
                pojo_name=pojo_name,
                properties=properties,
            )
            project.overwrite(path, contents)

        LOG.debug("Generate complete")


    def package(self, handler_path):
        template = resource_yaml(
            __name__, "data/CloudFormationHandlerInfrastructure.yaml"
        )
        self._create_or_update_stack(self.INFRA_STACK, json.dumps(template))
        bucket_name = self._get_stack_output(self.INFRA_STACK, "BucketName")

        handler_template = resource_yaml(__name__, "data/Handlers.yaml")
        self._package_lambda(handler_path, bucket_name, handler_template)
        self._create_or_update_stack(self.HANDLER_STACK, json.dumps(handler_template))

    def _create_or_update_stack(self, stack_name, template_body):
        args = {
            "StackName": stack_name,
            "TemplateBody": template_body,
            "Capabilities": ["CAPABILITY_IAM", "CAPABILITY_AUTO_EXPAND"],
        }
        try:
            LOG.info("Creating stack '%s'", stack_name)
            self._cfn_client.create_stack(**args)
        except self._cfn_client.exceptions.AlreadyExistsException:
            try:
                LOG.info(
                    "Stack '%s' already exists. Attempting to update stack", stack_name
                )
                self._cfn_client.update_stack(**args)
            except botocore.exceptions.ClientError as e:
                msg = str(e)
                if all(
                    s in msg
                    for s in ("UpdateStack", "ValidationError", "updates", "performed")
                ):
                    LOG.info("No updates to be performed for stack '%s'", stack_name)
                else:
                    raise
            else:
                self._stack_wait(stack_name, "stack_update_complete")
                LOG.info("Stack '%s' successfully updated", stack_name)
        else:
            self._stack_wait(stack_name, "stack_create_complete")
            LOG.info("Stack '%s' successfully created", stack_name)

    def _stack_wait(self, stack_name, terminal_state):
        waiter = self._cfn_client.get_waiter(terminal_state)
        waiter.wait(StackName=stack_name, WaiterConfig={"Delay": 5, "MaxAttempts": 200})

    def _package_lambda(self, handler_path, bucket_name, template):
        LOG.info("Uploading file '%s' to bucket '%s'", handler_path, bucket_name)
        self._s3_client.upload_file(handler_path, bucket_name, handler_path)

        response = self._s3_client.list_object_versions(
            Bucket=bucket_name, Prefix=handler_path, MaxKeys=1
        )
        version = response["Versions"][0]
        template["Resources"]["ResourceHandler"]["Properties"]["CodeUri"] = {
            "Bucket": bucket_name,
            "Key": handler_path,
            "Version": version["VersionId"],
        }

    def _get_stack_output(self, stack_name, output_key):
        result = self._cfn_client.describe_stacks(StackName=stack_name)
        outputs = result["Stacks"][0]["Outputs"]
        for output in outputs:
            if output["OutputKey"] == output_key:
                return output["OutputValue"]
        return None
