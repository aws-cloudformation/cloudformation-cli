# pylint: disable=useless-super-delegation,too-many-locals
# pylint doesn't recognize abstract methods
import logging
import shutil
from pathlib import Path

from rpdk.data_loaders import copy_resource
from rpdk.filters import resource_type_resource
from rpdk.jsonutils.jsonschema_flattener import JsonSchemaFlattener
from rpdk.plugin_base import LanguagePlugin

from .pojo_resolver import JavaPojoResolver

LOG = logging.getLogger(__name__)


class JavaLanguagePlugin(LanguagePlugin):
    MODULE_NAME = __name__
    NAME = "java"

    def __init__(self):
        self.env = self._setup_jinja_env(
            trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True
        )
        self._java_pojo_resolver = None

    def project_settings_defaults(self):
        return super().project_settings_defaults()

    def project_settings_schema(self):
        return super().project_settings_schema()

    def init(self, project_settings):
        LOG.info("Setting up package directories...")

        project_settings["buildSystem"] = "maven"
        project_settings["output_directory"] = Path(
            project_settings["output_directory"]
        ).resolve(strict=True)
        self._initialize_maven(project_settings)
        self._initialize_intellij(project_settings)

    def _initialize_intellij(self, project_settings):
        intellij_conf_dir = project_settings["output_directory"] / ".idea"
        intellij_conf_dir.mkdir(exist_ok=True)

        resource_schema_out = (
            project_settings["output_directory"] / "provider.definition.schema.v1.json"
        )

        copy_resource(
            "rpdk",
            "data/schema/provider.definition.schema.v1.json",
            resource_schema_out,
        )

        misc_template = self.env.get_template("intellij/misc.xml")
        with open(intellij_conf_dir / "misc.xml", "w", encoding="utf-8") as f:
            f.write(misc_template.render(project_settings))

        copy_resource(
            __name__, "data/jsonSchemas.xml", intellij_conf_dir / "jsonSchemas.xml"
        )

    def _initialize_maven(self, project_settings):
        output_pom = project_settings["output_directory"] / "pom.xml"
        pom_template = self.env.get_template("maven/pom.xml")
        with output_pom.open("w", encoding="utf-8") as f:
            f.write(pom_template.render(project_settings))

    def generate(self, resource_def, project_settings):
        LOG.info("Starting code generation...")
        output_directory = Path(project_settings["output_directory"])

        package_components = project_settings["packageName"].split(".")
        generated_src_main_dir = output_directory.joinpath(
            "generated-src", *package_components
        )
        src_main_dir = output_directory.joinpath("src", *package_components)
        generated_tst_main_dir = output_directory.joinpath("tst", *package_components)

        # eradicate any content from a prior codegen run
        shutil.rmtree(generated_src_main_dir, ignore_errors=True)
        shutil.rmtree(generated_tst_main_dir, ignore_errors=True)

        pojos_directory = generated_src_main_dir / "models"
        base_handlers_directory = generated_src_main_dir / "handlers"
        stub_handlers_directory = src_main_dir / "handlers"
        unit_tests_directory = generated_tst_main_dir

        # package files
        interfaces_directory = generated_src_main_dir / "interfaces"
        messages_directory = generated_src_main_dir / "messages"

        for directory in (
            pojos_directory,
            interfaces_directory,
            messages_directory,
            base_handlers_directory,
            stub_handlers_directory,
            unit_tests_directory,
        ):
            directory.mkdir(parents=True, exist_ok=True)
            LOG.debug("Created directory %s", directory)

        self.build_pojo_resolver(resource_def)

        self.generate_pojos(project_settings, pojos_directory)
        self.generate_package(project_settings, "messages", messages_directory)
        self.generate_package(project_settings, "interfaces", interfaces_directory)
        self.generate_base_handlers(project_settings, base_handlers_directory)
        self.generate_stub_handlers(project_settings, stub_handlers_directory)

    def build_pojo_resolver(self, resource_def):
        flattener = JsonSchemaFlattener(resource_def)
        flattened_map = flattener.flatten_schema()
        LOG.debug("Flattened Schema Map: %s", flattened_map)
        self._java_pojo_resolver = JavaPojoResolver(
            flattened_map, resource_type_resource(resource_def["typeName"])
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
        for path in self.env.list_templates(
            filter_func=lambda x: x.startswith(input_directory)
        ):
            template = self.env.get_template(path)
            output_filepath = Path(output_directory) / path.replace(
                "{}/".format(input_directory), ""
            )
            with output_filepath.open("w", encoding="utf-8") as f:
                f.write(template.render(**project_settings))
            LOG.debug("Created Package file %s", output_filepath)

    def generate_base_handlers(self, project_settings, output_directory):
        LOG.info("Generating Base Handlers...")

        resource_type = self._java_pojo_resolver.resource_class_name
        operations = ["Create", "Read", "Update", "Delete", "List"]

        # writes a jinja subclass to the templates folder and adds the handlers
        for operation in operations:
            base_handler_file = "Base{}Handler.java".format(operation)
            base_template = self.env.get_template(
                "handlers/{}".format(base_handler_file)
            )
            base_output_filepath = Path(output_directory) / base_handler_file
            with base_output_filepath.open("w", encoding="utf-8") as f:
                f.write(
                    base_template.render(
                        operation=operation, pojo_name=resource_type, **project_settings
                    )
                )
            LOG.debug("Created BaseHandler file %s", base_output_filepath)

    def generate_stub_handlers(self, project_settings, output_directory):
        LOG.info("Generating Handlers...")

        resource_type = self._java_pojo_resolver.resource_class_name
        operations = ["Create", "Read", "Update", "Delete", "List"]

        # writes a jinja subclass to the templates folder and adds the handlers
        for operation in operations:
            stub_handler_file = "{}Handler.java".format(operation)
            stub_template = self.env.get_template("handlers/StubHandler.java")
            output_filepath = Path(output_directory) / stub_handler_file
            # we do not overwrite the handler implementations
            if not output_filepath.exists():
                with output_filepath.open("w", encoding="utf-8") as f:
                    f.write(
                        stub_template.render(
                            operation=operation,
                            pojo_name=resource_type,
                            **project_settings,
                        )
                    )
                LOG.debug("Created Handler file %s", output_filepath)
