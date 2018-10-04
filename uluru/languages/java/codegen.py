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

    def init(self, project_settings):
        project_settings["output_directory"] = Path(
            project_settings["output_directory"]
        ).resolve(strict=True)
        self._initialize_intellij(project_settings)

    def _initialize_intellij(self, project_settings):
        intellij_conf_dir = project_settings["output_directory"] / ".idea"
        intellij_conf_dir.mkdir(exist_ok=True)

        resource_schema_stream = pkg_resources.resource_stream(
            "uluru", "data/schema/provider.definition.schema.v1.json"
        )
        resource_schema_out = (
            project_settings["output_directory"] / "provider.definition.schema.json"
        )
        with resource_schema_out.open("wb") as f:
            shutil.copyfileobj(resource_schema_stream, f)

        misc_template = self.env.get_template("intellij/misc.xml")
        with open(intellij_conf_dir / "misc.xml", "w", encoding="utf-8") as f:
            f.write(misc_template.render(project_settings))

        json_schemas_stream = pkg_resources.resource_stream(
            __name__, "templates/intellij/jsonSchemas.xml"
        )
        json_schemas_out = intellij_conf_dir / "jsonSchemas.xml"
        with json_schemas_out.open("wb") as f:
            shutil.copyfileobj(json_schemas_stream, f)

    def _initialize_maven(self, resource_type, project_settings):
        LOG.info("Initializing maven...")
        output_pom = Path(project_settings["output_directory"]) / "pom.xml"
        pom_template = self.env.get_template("maven/pom.xml")
        with output_pom.open("w", encoding="utf-8") as f:
            f.write(
                pom_template.render(resource_type=resource_type, **project_settings)
            )

    def generate(self, resource_def, project_settings):
        self._initialize_maven(resource_def["resourceType"], project_settings)
        LOG.info("Setting up package directories...")
        output_directory = Path(project_settings["output_directory"]).resolve(
            strict=True
        )

        package_name_dir = project_settings["packageName"].split(".")
        src_main_dir = output_directory.joinpath("src", *package_name_dir)
        tst_main_dir = output_directory.joinpath("tst", *package_name_dir)

        handlers_dir = src_main_dir / "handlers"

        unit_tests_dir = tst_main_dir / "unit"

        for directory in (handlers_dir, unit_tests_dir):
            directory.mkdir(parents=True, exist_ok=True)
            LOG.debug("Created directory %s", directory)

        self._generate_handlers(resource_def, project_settings, handlers_dir)

        self._generate_unit_tests(resource_def, project_settings, unit_tests_dir)

    def _generate_handlers(self, resource_def, project_settings, output_directory):
        LOG.info("Generating handlers...")

    def _generate_unit_tests(self, resource_def, project_settings, output_directory):
        LOG.info("Generating unit tests...")
