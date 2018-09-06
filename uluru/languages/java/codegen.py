# pylint: disable=useless-super-delegation,too-many-locals
# pylint doesn't recognize abstract methods
import logging
import shutil
from pathlib import Path

import pkg_resources

from uluru.plugin_base import LanguagePlugin

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

    def generate(self, resource_def, project_settings):
        namespace, service_name, resource_name = resource_def["Type"].split("::")

        curdl = ("Create", "Update", "Read", "Delete", "List")
        output_directory = Path(project_settings["output_directory"]).resolve(
            strict=True
        )
        package_name_prefix = project_settings["packageNamePrefix"]

        project_settings.setdefault("Client", {})
        java_client_keys = ["Client", "Builder", "ResourceModel"]
        for key in java_client_keys:
            project_settings["Client"].setdefault(key, key.upper())

        project_directory = package_name_prefix.split(".")

        source_directory = output_directory.joinpath("src", *project_directory)
        test_directory = output_directory.joinpath("tst", *project_directory)

        LOG.info("Creating output directory...")
        for dir_name in ("handlers", "models", "utils"):
            directory = source_directory / dir_name
            LOG.debug("Creating %s", directory)
            directory.mkdir(parents=True, exist_ok=True)

        for dir_name in ("unit", "integration"):
            directory = test_directory / dir_name
            LOG.debug("Creating %s", directory)
            directory.mkdir(parents=True, exist_ok=True)

        # dictionary maps template_path: output_path
        templates_and_outputs = [
            (
                "models/ResourceModel.java",
                source_directory / "models" / "{}Model.java".format(resource_name),
            ),
            (
                "utils/ClientBuilder.java",
                source_directory
                / "utils"
                / "{}ClientBuilder.java".format(service_name),
            ),
            (
                "utils/ResourceResponseReturner.java",
                source_directory
                / "utils"
                / "{}.java".format("ResourceResponseReturner"),
            ),
            ("unit/TestBase.java", test_directory / "unit" / "TestBase.java"),
            (
                "integration/IntegrationTests.java",
                test_directory
                / "integration"
                / "{}IntegrationTests.java".format(resource_name),
            ),
        ]
        templates_and_outputs.extend(
            (
                "handlers/{}Handler.java".format(handler_type),
                source_directory
                / "handlers"
                / "{}{}Handler.java".format(resource_name, handler_type),
            )
            for handler_type in curdl
        )
        templates_and_outputs.extend(
            (
                "unit/{}HandlerUnitTests.java".format(handler_type),
                test_directory
                / "unit"
                / "{}{}HandlerUnitTests.java".format(resource_name, handler_type),
            )
            for handler_type in curdl
        )

        # writes a jinja subclass to the templates folder and adds the subresource
        # template:output pair to the dictionary.
        template_path = "models/ResourceModel.java"
        template = self.env.get_template(template_path)
        defs = resource_def["Definitions"]
        try:
            for definition_name, definition_properties in defs.items():
                # not sure how to format long line above
                definition_properties = definition_properties["Properties"]
                def_output_path = (
                    source_directory / "models" / "{}Model.java".format(definition_name)
                )
                with def_output_path.open("w", encoding="utf-8") as f:
                    f.write(
                        template.render(
                            **resource_def,
                            **project_settings,
                            resource_name=definition_name,
                            resource_properties=definition_properties,
                        )
                    )
        except KeyError:
            LOG.exception("ERROR")  # what would cause this?

        for template_path, output_path in templates_and_outputs:
            template = self.env.get_template(template_path)
            with output_path.open("w", encoding="utf-8") as f:
                f.write(
                    template.render(
                        **resource_def,
                        **project_settings,
                        namespace=namespace,
                        service_name=service_name,
                        resource_name=resource_name,
                        resource_properties=resource_def["Properties"],
                    )
                )

    def initialize(self, project_settings):
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
            "uluru", "data/resource_provider_schema.json"
        )
        resource_schema_out = (
            project_settings["output_directory"] / "resource_provider_schema.json"
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
