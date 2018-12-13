import json
import logging
from pathlib import Path

from jsonschema import Draft6Validator
from jsonschema.exceptions import ValidationError

from .data_loaders import load_resource_spec, resource_json
from .plugin_registry import load_plugin

LOG = logging.getLogger(__name__)

SETTINGS_FILENAME = ".rpdk-config"
TYPE_NAME_REGEX = "^[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}$"

SETTINGS_VALIDATOR = Draft6Validator(
    {
        "properties": {
            "language": {"type": "string"},
            "typeName": {"type": "string", "pattern": TYPE_NAME_REGEX},
            "settings": {"type": "object"},
            "handlerArn": {"type": ["string", "null"]},
            "handlerTemplatePath": {"type": "string"},
        },
        "required": ["language", "typeName"],
        "additionalProperties": False,
    }
)


class InvalidSettingsError(Exception):
    pass


class Project:  # pylint: disable=too-many-instance-attributes
    def __init__(self, overwrite=False, root=None):
        self._overwrite = overwrite
        self.root = Path(root) if root else Path.cwd()
        self.settings_path = self.root / SETTINGS_FILENAME
        self.type_info = None
        self._plugin = None
        self.settings = None
        self.schema = None
        self.handler_arn = None
        self.handler_template_path = None

        LOG.debug("Root directory: %s", self.root)

    @property
    def language(self):
        return self._plugin.NAME

    @property
    def type_name(self):
        return "::".join(self.type_info)

    @type_name.setter
    def type_name(self, value):
        self.type_info = tuple(value.split("::"))

    @property
    def hypenated_name(self):
        return "-".join(self.type_info).lower()

    @property
    def schema_filename(self):
        return "{}.json".format(self.hypenated_name)

    @property
    def schema_path(self):
        return self.root / self.schema_filename

    def load_settings(self):
        def _invalid_settings(e):
            msg = "Project file '{}' is invalid".format(self.settings_path)
            LOG.critical(msg)
            LOG.debug(msg, exc_info=True)
            raise InvalidSettingsError(msg) from e

        LOG.debug("Loading project file '%s'", self.settings_path)
        try:
            with self.settings_path.open("r", encoding="utf-8") as f:
                raw_settings = json.load(f)
        except json.JSONDecodeError as e:
            _invalid_settings(e)

        try:
            SETTINGS_VALIDATOR.validate(raw_settings)
        except ValidationError as e:
            _invalid_settings(e)

        self.type_name = raw_settings["typeName"]
        self._plugin = load_plugin(raw_settings["language"])
        self.handler_template_path = raw_settings["handlerTemplatePath"]
        self.handler_arn = raw_settings["handlerArn"]
        self.settings = raw_settings.get("settings", {})

    def _write_example_schema(self):
        self.schema = resource_json(
            __name__, "data/examples/resource/initech.tps.report.v1.json"
        )
        self.schema["$id"] = self.schema_filename
        self.schema["typeName"] = self.type_name
        self.safewrite(self.schema_path, json.dumps(self.schema, indent=4))

    def _write_settings(self, language):
        raw_settings = {
            "typeName": self.type_name,
            "language": language,
            "settings": self.settings,
            "handlerTemplatePath": self.handler_template_path,
            "handlerArn": self.handler_arn,
        }
        self.overwrite(self.settings_path, json.dumps(raw_settings, indent=4))

    def init(self, type_name, language):
        self.type_name = type_name
        self._plugin = load_plugin(language)
        self.settings = {}

        self._write_example_schema()
        self._plugin.init(self)
        self._write_settings(language)

    def load_schema(self):
        if not self.type_info:
            msg = "Internal error (Must load settings first)"
            LOG.critical(msg)
            raise RuntimeError(msg)

        with self.schema_path.open("r", encoding="utf-8") as f:
            self.schema = load_resource_spec(f)

    @staticmethod
    def overwrite(path, contents):
        LOG.debug("Overwriting '%s'", path)
        with path.open("w", encoding="utf-8") as f:
            f.write(contents)

    def safewrite(self, path, contents):
        if self._overwrite:
            self.overwrite(path, contents)
        else:
            try:
                with path.open("x", encoding="utf-8") as f:
                    f.write(contents)
            except FileExistsError:
                LOG.warning("File already exists, not overwriting '%s'", path)

    def generate(self):
        return self._plugin.generate(self)

    def package(self):
        self.handler_arn = self._plugin.package(self.handler_template_path)
        self._write_settings(self.language)
