# pylint: disable=useless-super-delegation,too-many-locals
# pylint doesn't recognize abstract methods
import logging
import shutil
from pathlib import Path

import pkg_resources

from uluru.filters import resource_type_resource
from uluru.jsonutils.json_schema_normalizer import JsonSchemaNormalizer
from uluru.plugin_base import LanguagePlugin

from .pojo_resolver import JavaPojoResolver

LOG = logging.getLogger(__name__)


class JavaLanguagePlugin(LanguagePlugin):
    MODULE_NAME = __name__
    NAME = "java"

    def __init__(self):
        self.env = self._setup_jinja_env(
            trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True
        )

    def project_settings_defaults(self):
        return super().project_settings_defaults()

    def project_settings_schema(self):
        return super().project_settings_schema()

    def init(self, project_settings):
        LOG.info("Setting up package directories...")
        output_directory = Path(project_settings["output_directory"])
        output_directory.mkdir(exist_ok=True)

        project_settings["buildSystem"] = "maven"
        project_settings["output_directory"] = Path(
            project_settings["output_directory"]
        ).resolve(strict=True)
        self._initialize_maven(project_settings)
        self._initialize_intellij(project_settings)

    def _initialize_intellij(self, project_settings):
        intellij_conf_dir = project_settings["output_directory"] / ".idea"
        intellij_conf_dir.mkdir(exist_ok=True)

        resource_schema_stream = pkg_resources.resource_stream(
            "uluru", "data/schema/provider.definition.schema.v1.json"
        )
        resource_schema_out = (
            project_settings["output_directory"] / "provider.definition.schema.v1.json"
        )
        with resource_schema_out.open("wb") as f:
            shutil.copyfileobj(resource_schema_stream, f)

        misc_template = self.env.get_template("intellij/misc.xml")
        with open(intellij_conf_dir / "misc.xml", "w", encoding="utf-8") as f:
            f.write(misc_template.render(project_settings))

        json_schemas_stream = pkg_resources.resource_stream(
            __name__, "data/jsonSchemas.xml"
        )
        json_schemas_out = intellij_conf_dir / "jsonSchemas.xml"
        with json_schemas_out.open("wb") as f:
            shutil.copyfileobj(json_schemas_stream, f)

    def _initialize_maven(self, project_settings):
        output_pom = project_settings["output_directory"] / "pom.xml"
        pom_template = self.env.get_template("maven/pom.xml")
        with output_pom.open("w", encoding="utf-8") as f:
            f.write(pom_template.render(project_settings))

    def generate(self, resource_def, project_settings):
        LOG.info("Starting code generation...")
        output_directory = Path(project_settings["output_directory"])
        output_directory.mkdir(exist_ok=True)

        package_components = project_settings["packageName"].split(".")
        src_main_dir = output_directory.joinpath("generated-src", *package_components)
        tst_main_dir = output_directory.joinpath("tst", *package_components)

        # eradicate any content from a prior codegen run
        shutil.rmtree(src_main_dir)
        shutil.rmtree(tst_main_dir)

        pojos_directory = src_main_dir / "models"
        handlers_directory = src_main_dir / "handlers"
        unit_tests_directory = tst_main_dir

        # package files
        interfaces_directory = src_main_dir / "interfaces"
        messages_directory = src_main_dir / "messages"

        for directory in (
            pojos_directory,
            interfaces_directory,
            messages_directory,
            handlers_directory,
            unit_tests_directory,
        ):
            directory.mkdir(parents=True, exist_ok=True)
            LOG.debug("Created directory %s", directory)

        self._java_pojo_resolver = self.build_pojo_resolver(resource_def)

        self.generate_pojos(project_settings, pojos_directory)
        self.generate_package(project_settings, "messages", messages_directory)
        self.generate_package(project_settings, "interfaces", interfaces_directory)
        self.generate_handlers(project_settings, handlers_directory)
        self.generate_unit_tests(resource_def, project_settings, unit_tests_directory)

    def build_pojo_resolver(self, resource_def):
        normalizer = JsonSchemaNormalizer(resource_def)
        normalized_map = normalizer.collapse_and_resolve_schema()
        LOG.debug("Normalized Schema Map: %s", normalized_map)
        return JavaPojoResolver(
            normalized_map, resource_type_resource(resource_def["typeName"])
        )

    def generate_pojos(self, project_settings, output_directory):
        LOG.info("Generating POJOs...")

        pojos = self._java_pojo_resolver.resolve_pojos()
        LOG.debug("Pojos: %s", pojos)

        # writes a jinja subclass to the templates folder and adds the subresource
        # template:output pair to the dictionary.
        template = self.env.get_template("models/ResourceModel.java")
        for class_name, resource_properties in pojos.items():
            output_filepath = Path(output_directory) / (class_name + ".java")
            with output_filepath.open("w", encoding="utf-8") as f:
                f.write(
                    template.render(
                        class_name=class_name,
                        resource_properties=resource_properties,
                        **project_settings,
                    )
                )
            LOG.debug("Created POJO file %s", output_filepath)

    def generate_package(self, project_settings, input_directory, output_directory):
        LOG.info("Generating Package Code...")

        # writes a jinja subclass to the templates folder and adds the handlers
        for p in self.env.list_templates(
            filter_func=lambda x: x.startswith(input_directory)
        ):
            template = self.env.get_template(p)
            output_filepath = Path(output_directory) / p.replace(
                "{}/".format(input_directory), ""
            )
            with output_filepath.open("w", encoding="utf-8") as f:
                f.write(template.render(**project_settings))
            LOG.debug("Created Package file %s", output_filepath)

    def generate_handlers(self, project_settings, output_directory):
        LOG.info("Generating Handlers...")

        resource_type = self._java_pojo_resolver.normalized_resource_type_name()
        operations = ["Create", "Read", "Update", "Delete", "List"]

        # writes a jinja subclass to the templates folder and adds the handlers
        for operation in operations:
            handlerFile = "Base{}Handler.java".format(operation)
            template = self.env.get_template("handlers/{}".format(handlerFile))
            output_filepath = Path(output_directory) / handlerFile
            with output_filepath.open("w", encoding="utf-8") as f:
                f.write(
                    template.render(
                        operation=operation, pojo_name=resource_type, **project_settings
                    )
                )
            LOG.debug("Created Handler file %s", output_filepath)

    def generate_unit_tests(self, resource_def, project_settings, output_directory):
        LOG.info("Generating Unit Tests...")
