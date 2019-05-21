import json
import logging
import zipfile
from pathlib import Path
from tempfile import TemporaryFile

from jsonschema import Draft6Validator
from jsonschema.exceptions import ValidationError

from .boto_helpers import create_sdk_session
from .data_loaders import load_resource_spec, resource_json
from .exceptions import InternalError, InvalidProjectError, SpecValidationError
from .plugin_registry import load_plugin
from .upload import Uploader

LOG = logging.getLogger(__name__)

SETTINGS_FILENAME = ".rpdk-config"
SCHEMA_UPLOAD_FILENAME = "schema.json"
TYPE_NAME_REGEX = "^[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}$"


LAMBDA_RUNTIMES = {
    "noexec",  # cannot be executed, schema only
    "java8",
    "go1.x",
    # python2.7 is EOL soon (2020-01-01)
    "python3.6",
    "python3.7",
    # dotnetcore1.0 is EOL soon (2019-06-27)
    "dotnetcore2.1",
    # nodejs8.10 is EOL soon (2019-12-??)
    "nodejs10.x",
}

SETTINGS_VALIDATOR = Draft6Validator(
    {
        "properties": {
            "language": {"type": "string"},
            "typeName": {"type": "string", "pattern": TYPE_NAME_REGEX},
            "runtime": {"type": "string", "enum": list(LAMBDA_RUNTIMES)},
            "entrypoint": {"type": ["string", "null"]},
            "settings": {"type": "object"},
        },
        "required": ["language", "typeName", "runtime", "entrypoint"],
        "additionalProperties": False,
    }
)


class Project:  # pylint: disable=too-many-instance-attributes
    def __init__(self, overwrite_enabled=False, root=None):
        self.overwrite_enabled = overwrite_enabled
        self.root = Path(root) if root else Path.cwd()
        self.settings_path = self.root / SETTINGS_FILENAME
        self.type_info = None
        self._plugin = None
        self.settings = None
        self.schema = None
        self.runtime = "noexec"
        self.entrypoint = None

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

    @staticmethod
    def _raise_invalid_project(msg, e):
        LOG.debug(msg, exc_info=e)
        raise InvalidProjectError(msg) from e

    def load_settings(self):
        LOG.debug("Loading project file '%s'", self.settings_path)
        try:
            with self.settings_path.open("r", encoding="utf-8") as f:
                raw_settings = json.load(f)
        except json.JSONDecodeError as e:
            self._raise_invalid_project(
                "Project file '{}' is invalid".format(self.settings_path), e
            )

        try:
            SETTINGS_VALIDATOR.validate(raw_settings)
        except ValidationError as e:
            self._raise_invalid_project(
                "Project file '{}' is invalid".format(self.settings_path), e
            )

        self.type_name = raw_settings["typeName"]
        self.runtime = raw_settings["runtime"]
        self.entrypoint = raw_settings["entrypoint"]
        self._plugin = load_plugin(raw_settings["language"])
        self.settings = raw_settings.get("settings", {})

    def _write_example_schema(self):
        self.schema = resource_json(
            __name__, "data/examples/resource/initech.tps.report.v1.json"
        )
        self.schema["typeName"] = self.type_name
        self.safewrite(self.schema_path, json.dumps(self.schema, indent=4))

    def _write_settings(self, language):
        if self.runtime not in LAMBDA_RUNTIMES:
            LOG.critical(
                "Plugin returned invalid runtime: %s (%s)", self.runtime, language
            )
            raise InternalError("Internal error (Plugin returned invalid runtime)")

        raw_settings = {
            "typeName": self.type_name,
            "language": language,
            "runtime": self.runtime,
            "entrypoint": self.entrypoint,
            "settings": self.settings,
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
            raise InternalError(msg)

        with self.schema_path.open("r", encoding="utf-8") as f:
            self.schema = load_resource_spec(f)

    @staticmethod
    def overwrite(path, contents):
        LOG.debug("Overwriting '%s'", path)
        with path.open("w", encoding="utf-8") as f:
            f.write(contents)

    def safewrite(self, path, contents):
        if self.overwrite_enabled:
            self.overwrite(path, contents)
        else:
            try:
                with path.open("x", encoding="utf-8") as f:
                    f.write(contents)
            except FileExistsError:
                LOG.warning("File already exists, not overwriting '%s'", path)

    def generate(self):
        return self._plugin.generate(self)

    def load(self):
        try:
            self.load_settings()
        except FileNotFoundError as e:
            self._raise_invalid_project(
                "Project file not found. Have you run 'init'?", e
            )

        LOG.info("Validating your resource specification...")
        try:
            self.load_schema()
        except FileNotFoundError as e:
            self._raise_invalid_project("Resource specification not found.", e)
        except SpecValidationError as e:
            msg = "Resource specification is invalid: " + str(e)
            self._raise_invalid_project(msg, e)

    def submit(self, dry_run, endpoint_url, region_name):
        # if it's a dry run, keep the file; otherwise can delete after upload
        if dry_run:
            path = Path("{}.zip".format(self.hypenated_name))
            context_mgr = path.open("wb")
        else:
            context_mgr = TemporaryFile("w+b")

        with context_mgr as f:
            # the default compression is ZIP_STORED, which helps with the
            # file-size check on upload
            with zipfile.ZipFile(f, mode="w") as zip_file:
                zip_file.write(self.schema_path, SCHEMA_UPLOAD_FILENAME)
                zip_file.write(self.settings_path, SETTINGS_FILENAME)
                self._plugin.package(self, zip_file)

            if dry_run:
                LOG.error("Dry run complete: %s", path.resolve())
            else:
                f.seek(0)
                self._upload(f, endpoint_url=endpoint_url, region_name=region_name)

    def _upload(self, fileobj, endpoint_url, region_name):
        LOG.debug("Packaging complete, uploading...")
        session = create_sdk_session()
        cfn_client = session.client(
            "cloudformation", region_name=region_name, endpoint_url=endpoint_url
        )
        s3_client = session.client("s3", region_name=region_name)
        s3_url = Uploader(cfn_client, s3_client).upload(self.hypenated_name, fileobj)
        LOG.debug("Got S3 URL: %s", s3_url)

        response = cfn_client.register_resource_type(
            SchemaHandlerPackage=s3_url, TypeName=self.type_name
        )
        LOG.warning(
            "Registration in progress with token: %s", response["RegistrationToken"]
        )
