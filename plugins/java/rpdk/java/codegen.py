# pylint: disable=useless-super-delegation,too-many-locals
# pylint doesn't recognize abstract methods
import logging
import shutil

from rpdk.core.jsonutils.flattener import JsonSchemaFlattener
from rpdk.core.plugin_base import LanguagePlugin

from .pojo_resolver import JavaPojoResolver
from .utils import safe_reserved

LOG = logging.getLogger(__name__)

OPERATIONS = ("Create", "Read", "Update", "Delete", "List")
EXECUTABLE = "uluru-cli"


class JavaLanguagePlugin(LanguagePlugin):
    MODULE_NAME = __name__
    NAME = "java"
    RUNTIME = "java8"
    ENTRY_POINT = "{}.HandlerWrapper::handleRequest"
    CODE_URI = "./target/{}-1.0-SNAPSHOT.jar"

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
        artifact_id = "{}-handler".format(project.hypenated_name)
        contents = template.render(
            group_id=self.package_name, artifact_id=artifact_id, executable=EXECUTABLE
        )
        project.safewrite(path, contents)

        # CloudFormation/SAM template for handler lambda
        path = project.root / "Handler.yaml"
        LOG.debug("Writing SAM template: %s", path)
        template = self.env.get_template("Handler.yaml")
        contents = template.render(
            resource_type=project.type_name,
            handler_params={
                "Handler": self.ENTRY_POINT.format(self.package_name),
                "Runtime": self.RUNTIME,
                "CodeUri": self.CODE_URI.format(artifact_id),
            },
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

        path = src / "HandlerWrapper.java"
        LOG.debug("Writing handler wrapper: %s", path)
        template = self.env.get_template("HandlerWrapper.java")
        contents = template.render(
            package_name=self.package_name,
            operations=OPERATIONS,
            pojo_name="ResourceModel",
        )
        project.overwrite(path, contents)

        path = src / "BaseConfiguration.java"
        LOG.debug("Writing base configuration: %s", path)
        template = self.env.get_template("BaseConfiguration.java")
        contents = template.render(package_name=self.package_name)
        project.overwrite(path, contents)

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

    def package(self, project):
        pass
