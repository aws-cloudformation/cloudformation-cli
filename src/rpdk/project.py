import json
import logging
from pathlib import Path

from jsonschema import Draft6Validator
from jsonschema.exceptions import ValidationError

from .boto_helpers import create_client
from .data_loaders import load_resource_spec, resource_json
from .packager import package_handler
from .plugin_registry import load_plugin

LOG = logging.getLogger(__name__)

SETTINGS_FILENAME = ".rpdk-config"
TYPE_NAME_REGEX = "^[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}$"
RESOURCE_EXISTS_MSG = "Resource already exists."
HANDLER_OPS = ("CREATE", "READ", "UPDATE", "DELETE", "LIST")

SETTINGS_VALIDATOR = Draft6Validator(
    {
        "properties": {
            "language": {"type": "string"},
            "typeName": {"type": "string", "pattern": TYPE_NAME_REGEX},
            "settings": {"type": "object"},
            "handlerArn": {"type": ["string", "null"]},
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

        LOG.debug("Root directory: %s", self.root)

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
        self._plugin.package(self)

        handler_stack_name = "{}-stack".format(self.hypenated_name)
        self.handler_arn = package_handler(handler_stack_name)

        self._write_settings(self._plugin.NAME)

    def submit(self):
        handler_arns = {op: self.handler_arn for op in HANDLER_OPS}

        registry_args = {
            "TypeName": self.type_name,
            "Schema": json.dumps(self.schema),
            "Handlers": handler_arns,
            # https://github.com/awslabs/aws-cloudformation-rpdk/issues/175
            "Documentation": "Docs",
        }
        client = create_client("cloudformation")

        try:
            response = client.create_resource_type(**registry_args)
            LOG.info("Created resource type with ARN '%s'", response["Arn"])
        except client.exceptions.CFNRegistryException as e:
            msg = str(e)
            # https://github.com/awslabs/aws-cloudformation-rpdk/issues/177
            if RESOURCE_EXISTS_MSG in msg:
                response = client.update_resource_type(**registry_args)
                LOG.info("Updated resource type with ARN '%s'", response["Arn"])
            else:
                raise
        return response["Arn"]
