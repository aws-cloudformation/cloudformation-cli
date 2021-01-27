import json
import logging
import os
import shutil
import zipfile
from pathlib import Path
from tempfile import TemporaryFile
from uuid import uuid4

from botocore.exceptions import ClientError, WaiterError
from jinja2 import Environment, PackageLoader, select_autoescape
from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError

from rpdk.core.fragment.generator import TemplateFragment
from rpdk.core.jsonutils.flattener import JsonSchemaFlattener

from . import __version__
from .boto_helpers import create_sdk_session
from .data_loaders import load_resource_spec, resource_json
from .exceptions import (
    DownstreamError,
    FragmentValidationError,
    InternalError,
    InvalidProjectError,
    SpecValidationError,
)
from .jsonutils.pointer import fragment_decode, fragment_encode
from .jsonutils.utils import traverse
from .plugin_registry import load_plugin
from .upload import Uploader

LOG = logging.getLogger(__name__)

SETTINGS_FILENAME = ".rpdk-config"
SCHEMA_UPLOAD_FILENAME = "schema.json"
OVERRIDES_FILENAME = "overrides.json"
INPUTS_FOLDER = "inputs"
EXAMPLE_INPUTS_FOLDER = "example_inputs"
ROLE_TEMPLATE_FILENAME = "resource-role.yaml"
TYPE_NAME_RESOURCE_REGEX = "^[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}$"
TYPE_NAME_MODULE_REGEX = (
    "^[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}::MODULE$"
)
ARTIFACT_TYPE_RESOURCE = "RESOURCE"
ARTIFACT_TYPE_MODULE = "MODULE"

DEFAULT_ROLE_TIMEOUT_MINUTES = 120  # 2 hours
# min and max are according to CreateRole API restrictions
# https://docs.aws.amazon.com/IAM/latest/APIReference/API_CreateRole.html
MIN_ROLE_TIMEOUT_SECONDS = 3600  # 1 hour
MAX_ROLE_TIMEOUT_SECONDS = 43200  # 12 hours

CFN_METADATA_FILENAME = ".cfn_metadata.json"

LAMBDA_RUNTIMES = {
    "noexec",  # cannot be executed, schema only
    "java8",
    "java11",
    "go1.x",
    "python3.6",
    "python3.7",
    "python3.8",
    "dotnetcore2.1",
    "nodejs10.x",
    "nodejs12.x",
}

SETTINGS_VALIDATOR = Draft7Validator(
    {
        "properties": {
            "artifact_type": {"type": "string"},
            "language": {"type": "string"},
            "typeName": {"type": "string", "pattern": TYPE_NAME_RESOURCE_REGEX},
            "runtime": {"type": "string", "enum": list(LAMBDA_RUNTIMES)},
            "entrypoint": {"type": ["string", "null"]},
            "testEntrypoint": {"type": ["string", "null"]},
            "executableEntrypoint": {"type": ["string", "null"]},
            "settings": {"type": "object"},
        },
        "required": ["language", "typeName", "runtime", "entrypoint"],
    }
)

MODULE_SETTINGS_VALIDATOR = Draft7Validator(
    {
        "properties": {
            "artifact_type": {"type": "string"},
            "typeName": {"type": "string", "pattern": TYPE_NAME_MODULE_REGEX},
            "settings": {"type": "object"},
        },
        "required": ["artifact_type", "typeName"],
    }
)


BASIC_TYPE_MAPPINGS = {
    "string": "String",
    "number": "Double",
    "integer": "Integer",
    "boolean": "Boolean",
}


MARKDOWN_RESERVED_CHARACTERS = frozenset({"^", "*", "+", ".", "(", "[", "{", "#"})


def escape_markdown(string):
    """Escapes the reserved Markdown characters."""
    if not string:
        return string
    if string[0] in MARKDOWN_RESERVED_CHARACTERS:
        return "\\{}".format(string)
    return string


class Project:  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    def __init__(self, overwrite_enabled=False, root=None):
        self.overwrite_enabled = overwrite_enabled
        self.root = Path(root) if root else Path.cwd()
        self.settings_path = self.root / SETTINGS_FILENAME
        self.type_info = None
        self.artifact_type = None
        self.language = None
        self._plugin = None
        self.settings = None
        self.schema = None
        self._flattened_schema = None
        self._marked_down_properties = {}
        self.runtime = "noexec"
        self.entrypoint = None
        self.test_entrypoint = None
        self.executable_entrypoint = None
        self.fragment_dir = None

        self.env = Environment(
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            loader=PackageLoader(__name__, "templates/"),
            autoescape=select_autoescape(["html", "htm", "xml", "md"]),
        )

        self.env.filters["escape_markdown"] = escape_markdown

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

    @property
    def overrides_path(self):
        return self.root / OVERRIDES_FILENAME

    @property
    def inputs_path(self):
        return self.root / INPUTS_FOLDER

    @property
    def example_inputs_path(self):
        return self.root / EXAMPLE_INPUTS_FOLDER

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

        # backward compatible
        if "artifact_type" not in raw_settings:
            raw_settings["artifact_type"] = ARTIFACT_TYPE_RESOURCE

        if raw_settings["artifact_type"] == ARTIFACT_TYPE_RESOURCE:
            self.validate_and_load_resource_settings(raw_settings)
        else:
            self.validate_and_load_module_settings(raw_settings)

    def validate_and_load_module_settings(self, raw_settings):
        try:
            MODULE_SETTINGS_VALIDATOR.validate(raw_settings)
        except ValidationError as e:
            self._raise_invalid_project(
                "Project file '{}' is invalid".format(self.settings_path), e
            )
        self.type_name = raw_settings["typeName"]
        self.artifact_type = raw_settings["artifact_type"]
        self.settings = raw_settings.get("settings", {})

    def validate_and_load_resource_settings(self, raw_settings):
        try:
            SETTINGS_VALIDATOR.validate(raw_settings)
        except ValidationError as e:
            self._raise_invalid_project(
                "Project file '{}' is invalid".format(self.settings_path), e
            )
        self.type_name = raw_settings["typeName"]
        self.artifact_type = raw_settings["artifact_type"]
        self.language = raw_settings["language"]
        self.runtime = raw_settings["runtime"]
        self.entrypoint = raw_settings["entrypoint"]
        self.test_entrypoint = raw_settings["testEntrypoint"]
        self.executable_entrypoint = raw_settings.get("executableEntrypoint")
        self._plugin = load_plugin(raw_settings["language"])
        self.settings = raw_settings.get("settings", {})

    def _write_example_schema(self):
        self.schema = resource_json(
            __name__, "data/examples/resource/initech.tps.report.v1.json"
        )
        self.schema["typeName"] = self.type_name

        def _write(f):
            json.dump(self.schema, f, indent=4)
            f.write("\n")

        self.safewrite(self.schema_path, _write)

    def _write_example_inputs(self):

        shutil.rmtree(self.example_inputs_path, ignore_errors=True)
        self.example_inputs_path.mkdir(exist_ok=True)

        template = self.env.get_template("inputs.json")
        properties = list(self.schema["properties"].keys())

        for inputs_file in (
            "inputs_1_create.json",
            "inputs_1_update.json",
            "inputs_1_invalid.json",
        ):
            self.safewrite(
                self.example_inputs_path / inputs_file,
                template.render(
                    properties=properties[:-1], last_property=properties[-1]
                ),
            )

    def write_settings(self):
        if self.runtime not in LAMBDA_RUNTIMES:
            LOG.critical(
                "Plugin returned invalid runtime: %s (%s)", self.runtime, self.language
            )
            raise InternalError("Internal error (Plugin returned invalid runtime)")

        def _write_resource_settings(f):
            executable_entrypoint_dict = (
                {"executableEntrypoint": self.executable_entrypoint}
                if self.executable_entrypoint
                else {}
            )
            json.dump(
                {
                    "artifact_type": self.artifact_type,
                    "typeName": self.type_name,
                    "language": self.language,
                    "runtime": self.runtime,
                    "entrypoint": self.entrypoint,
                    "testEntrypoint": self.test_entrypoint,
                    "settings": self.settings,
                    **executable_entrypoint_dict,
                },
                f,
                indent=4,
            )
            f.write("\n")

        def _write_module_settings(f):
            json.dump(
                {
                    "artifact_type": self.artifact_type,
                    "typeName": self.type_name,
                    "settings": self.settings,
                },
                f,
                indent=4,
            )
            f.write("\n")

        if self.artifact_type == ARTIFACT_TYPE_RESOURCE:
            self.overwrite(self.settings_path, _write_resource_settings)
        else:
            self.overwrite(self.settings_path, _write_module_settings)

    def init(self, type_name, language, settings=None):
        self.artifact_type = ARTIFACT_TYPE_RESOURCE
        self.type_name = type_name
        self.language = language
        self._plugin = load_plugin(language)
        self.settings = settings or {}
        self._write_example_schema()
        self._write_example_inputs()
        self._plugin.init(self)
        self.write_settings()

    def init_module(self, type_name):
        self.artifact_type = ARTIFACT_TYPE_MODULE
        self.type_name = type_name
        self.settings = {}
        self.write_settings()

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
            if callable(contents):
                contents(f)
            else:
                f.write(contents)

    def safewrite(self, path, contents):
        if self.overwrite_enabled:
            self.overwrite(path, contents)
        else:
            try:
                with path.open("x", encoding="utf-8") as f:
                    if callable(contents):
                        contents(f)
                    else:
                        f.write(contents)
            except FileExistsError:
                LOG.info("File already exists, not overwriting '%s'", path)

    def generate(self):
        if self.artifact_type == ARTIFACT_TYPE_MODULE:
            return  # for Modules, the schema is already generated in cfn validate

        # generate template for IAM role assumed by cloudformation
        # to provision resources if schema has handlers defined
        if "handlers" in self.schema:
            handlers = self.schema["handlers"]
            template = self.env.get_template("resource-role.yml")
            permission = "Allow"
            path = self.root / ROLE_TEMPLATE_FILENAME
            LOG.debug("Writing Resource Role CloudFormation template: %s", path)
            actions = {
                action
                for handler in handlers.values()
                for action in handler.get("permissions", [])
            }

            # calculate IAM role max session timeout based on highest handler timeout
            # with some buffer (70 seconds per minute)
            max_handler_timeout = max(
                (
                    handler.get("timeoutInMinutes", DEFAULT_ROLE_TIMEOUT_MINUTES)
                    for operation, handler in handlers.items()
                ),
                default=DEFAULT_ROLE_TIMEOUT_MINUTES,
            )
            # max role session timeout must be between 1 hour and 12 hours
            role_session_timeout = min(
                MAX_ROLE_TIMEOUT_SECONDS,
                max(MIN_ROLE_TIMEOUT_SECONDS, 70 * max_handler_timeout),
            )

            # gets rid of any empty string actions.
            # Empty strings cannot be specified as an action in an IAM statement
            actions.discard("")
            # Check if handler has actions
            if not actions:
                actions.add("*")
                permission = "Deny"

            contents = template.render(
                type_name=self.hypenated_name,
                actions=sorted(actions),
                permission=permission,
                role_session_timeout=role_session_timeout,
            )
            self.overwrite(path, contents)

        self._plugin.generate(self)

    def load(self):
        try:
            self.load_settings()
        except FileNotFoundError as e:
            self._raise_invalid_project(
                "Project file not found. Have you run 'init'?", e
            )

        if self.artifact_type == ARTIFACT_TYPE_MODULE:
            LOG.info("Validating your module fragments...")
            template_fragment = TemplateFragment(self.type_name)
            try:
                self._validate_fragments(template_fragment)
            except FragmentValidationError as e:
                msg = "Invalid template fragment: " + str(e)
                self._raise_invalid_project(msg, e)
            self.schema = template_fragment.generate_schema()
            self.fragment_dir = template_fragment.fragment_dir
        else:
            LOG.info("Validating your resource specification...")
            try:
                self.load_schema()
                LOG.warning("Resource schema is valid.")
            except FileNotFoundError as e:
                self._raise_invalid_project("Resource specification not found.", e)
            except SpecValidationError as e:
                msg = "Resource specification is invalid: " + str(e)
                self._raise_invalid_project(msg, e)

    @staticmethod
    def _validate_fragments(template_fragment):
        template_fragment.validate_fragments()

    # flake8: noqa: C901
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-public-methods
    def submit(
        self, dry_run, endpoint_url, region_name, role_arn, use_role, set_default
    ):  # pylint: disable=too-many-arguments
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
                zip_file.write(self.settings_path, SETTINGS_FILENAME)
                # Include all fragments in zip file
                if self.artifact_type == ARTIFACT_TYPE_MODULE:
                    if not os.path.exists(self.root / SCHEMA_UPLOAD_FILENAME):
                        msg = "Module schema could not be found."
                        raise InternalError(msg)
                    zip_file.write(
                        self.root / SCHEMA_UPLOAD_FILENAME, SCHEMA_UPLOAD_FILENAME
                    )
                    for root, _dirs, files in os.walk(self.fragment_dir):
                        for file in files:
                            zip_file.write(
                                os.path.join(root, file),
                                arcname=os.path.join(
                                    root.replace(str(self.fragment_dir), "fragments/"),
                                    file,
                                ),
                            )
                else:
                    zip_file.write(self.schema_path, SCHEMA_UPLOAD_FILENAME)
                try:
                    zip_file.write(self.overrides_path, OVERRIDES_FILENAME)
                    LOG.debug("%s found. Writing to package.", OVERRIDES_FILENAME)
                except FileNotFoundError:
                    LOG.debug(
                        "%s not found. Not writing to package.", OVERRIDES_FILENAME
                    )

                if self.artifact_type != ARTIFACT_TYPE_MODULE:
                    if os.path.isdir(self.inputs_path):
                        for filename in os.listdir(self.inputs_path):
                            absolute_path = self.inputs_path / filename
                            zip_file.write(
                                absolute_path, INPUTS_FOLDER + "/" + filename
                            )
                            LOG.debug("%s found. Writing to package.", filename)
                    else:
                        LOG.debug(
                            "%s not found. Not writing to package.", INPUTS_FOLDER
                        )
                    self._plugin.package(self, zip_file)

                    cli_metadata = {}

                    try:
                        cli_metadata = self._plugin.get_plugin_information(self)
                    except AttributeError:
                        LOG.debug(
                            "Version info is not available for plugins, not writing to metadata file"
                        )

                    cli_metadata["cli-version"] = __version__
                    zip_file.writestr(CFN_METADATA_FILENAME, json.dumps(cli_metadata))

            if dry_run:
                LOG.error("Dry run complete: %s", path.resolve())
            else:
                f.seek(0)
                self._upload(
                    f, endpoint_url, region_name, role_arn, use_role, set_default
                )

    def generate_docs(self):
        if self.artifact_type == ARTIFACT_TYPE_MODULE:
            return

        # generate the docs folder that contains documentation based on the schema
        docs_path = self.root / "docs"

        if not self.type_info or not self.schema or "properties" not in self.schema:
            LOG.warning(
                "Could not generate schema docs due to missing type info or schema"
            )
            return

        LOG.debug("Removing generated docs: %s", docs_path)
        shutil.rmtree(docs_path, ignore_errors=True)
        docs_path.mkdir(exist_ok=True)

        LOG.debug("Writing generated docs")

        # take care not to modify the master schema
        docs_schema = json.loads(json.dumps(self.schema))
        self._flattened_schema = JsonSchemaFlattener(
            json.loads(json.dumps(self.schema))
        ).flatten_schema()

        docs_schema["properties"] = {
            name: self._set_docs_properties(name, value, (name,))
            for name, value in self._flattened_schema[()]["properties"].items()
        }

        LOG.debug("Finished documenting nested properties")

        ref = self._get_docs_primary_identifier(docs_schema)
        getatt = self._get_docs_gettable_atts(docs_schema)

        readme_path = docs_path / "README.md"
        LOG.debug("Writing docs README: %s", readme_path)
        template = self.env.get_template("docs-readme.md")
        contents = template.render(
            type_name=self.type_name, schema=docs_schema, ref=ref, getatt=getatt
        )
        self.safewrite(readme_path, contents)

    def generate_image_build_config(self):
        if not hasattr(self._plugin, "generate_image_build_config"):
            raise InvalidProjectError(
                "Plugin for the {} runtime does not support building an image".format(
                    self.runtime
                )
            )
        return self._plugin.generate_image_build_config(self)

    @staticmethod
    def _get_docs_primary_identifier(docs_schema):
        try:
            primary_id = docs_schema["primaryIdentifier"]
            if len(primary_id) == 1:
                # drop /properties
                primary_id_path = fragment_decode(primary_id[0], prefix="")[1:]
                # at some point, someone might use a nested primary ID
                if len(primary_id_path) == 1:
                    return primary_id_path[0]
                LOG.warning("Nested primaryIdentifier found")
        except (KeyError, ValueError):
            pass
        return None

    @staticmethod
    def _get_docs_gettable_atts(docs_schema):
        def _get_property_description(prop):
            path = fragment_decode(prop, prefix="")
            name = path[-1]
            try:
                desc, _resolved_path, _parent = traverse(
                    docs_schema, path + ("description",)
                )
            except (KeyError, IndexError, ValueError):
                desc = f"Returns the <code>{name}</code> value."
            return {"name": name, "description": desc}

        return [
            _get_property_description(prop)
            for prop in docs_schema.get("readOnlyProperties", [])
        ]

    def _set_docs_properties(  # noqa: C901
        self, propname, prop, proppath
    ):  # pylint: disable=too-many-locals,too-many-statements
        """method sets markdown for each property;
        1. Supports multiple types per property - done via flattened schema so `allOf`,
        `anyOf`, `oneOf` combined into a collection then method iterates to reapply
        itself to each type
        2. Supports circular reference - done via pre calculating hypothetical .md file
        path and name
        which is reused once property is hit more than once

        Args:
            propname ([str]): property name
            prop ([dict]): all the sub propeties
            proppath ([tuple]): path of the property

        Returns:
            [dict]: modified sub dictionary with attached markdown
        """
        types = ("jsontype", "yamltype", "longformtype")
        jsontype, yamltype, longformtype = types

        # reattach prop from reference
        if "$ref" in prop:
            ref = self._flattened_schema[prop["$ref"]]
            propname = prop["$ref"][1]
            # this is to tie object to a definition and not to a property
            proppath = (propname,)
            prop = ref

        # this means method is traversing already visited property
        if propname in self._marked_down_properties:
            return {
                property_item: markdown
                for property_item, markdown in self._marked_down_properties[
                    propname
                ].items()
                if property_item in types
            }  # returning already set markdown

        proppath_ptr = fragment_encode(("properties",) + proppath, prefix="")
        if (
            "createOnlyProperties" in self.schema
            and proppath_ptr in self.schema["createOnlyProperties"]
        ):
            prop["createonly"] = True

        if (
            "readOnlyProperties" in self.schema
            and proppath_ptr in self.schema["readOnlyProperties"]
        ):
            prop["readonly"] = True

        # join multiple types
        def __join(item1, item2):
            if not item1 or item2 == item1:
                return item2
            return "{}, {}".format(item1, item2)

        def __set_property_type(prop_type, single_type=True):
            nonlocal prop

            # mark down formatting of the target value - used for complex objects
            # ($ref) and arrays of such objects
            markdown_lambda = (
                lambda fname, name: f'<a href="{fname}">{name}</a>'  # noqa: B950, C0301
            )

            type_json = type_yaml = type_longform = "Unknown"
            if prop_type in BASIC_TYPE_MAPPINGS:
                # primitives should not occur for circular ref;
                type_json = type_yaml = type_longform = BASIC_TYPE_MAPPINGS[prop_type]
            elif prop_type == "array":

                # lambdas to reuse formatting
                markdown_json = (
                    lambda markdown_value: f"[ {markdown_value}, ... ]"
                )  # noqa: E731
                markdown_yaml = lambda markdown_value: (  # noqa: E731
                    f"\n      - {markdown_value}"
                    if single_type
                    else f"[ {markdown_value}, ... ]"
                )
                markdown_long = (
                    lambda markdown_value: f"List of {markdown_value}"
                )  # noqa: E731

                # potential circular ref
                # setting up markdown before going deep in the heap to reuse markdown
                if "$ref" in prop["items"]:
                    sub_propname = prop["items"]["$ref"][1]  # get target sub property
                    sub_proppath = (sub_propname,)

                    # calculating hypothetical markdown property before
                    # actually traversing it - this way it could be reused -
                    # same .md doc could be attached to both instances
                    hypothetical = markdown_lambda(
                        "-".join(sub_proppath).lower() + ".md", sub_propname
                    )

                    # assigning hypothetical .md file reference before circular
                    # property gets boundary so when boundary is hit it reuses
                    # the same document
                    self._marked_down_properties[propname] = {
                        jsontype: markdown_json(hypothetical),
                        yamltype: markdown_yaml(hypothetical),
                        longformtype: markdown_long(hypothetical),
                    }

                # traverse nested propertes
                prop["arrayitems"] = arrayitems = self._set_docs_properties(
                    propname, prop["items"], proppath
                )

                # arrayitems should be similar to markdown of hypothetical target
                # if there is an object ref
                # arrayitems are could not be used for hypothetical values
                # as could not be populated before traversing down
                type_json = markdown_json(arrayitems[jsontype])
                type_yaml = markdown_yaml(arrayitems[yamltype])
                type_longform = markdown_long(arrayitems[longformtype])

            elif prop_type == "object":
                template = self.env.get_template("docs-subproperty.md")
                docs_path = self.root / "docs"

                object_properties = (
                    prop.get("properties") or prop.get("patternProperties") or {}
                )

                type_json = type_yaml = type_longform = "Map"
                if object_properties:

                    subproperty_name = " ".join(proppath)
                    subproperty_filename = "-".join(proppath).lower() + ".md"
                    subproperty_path = docs_path / subproperty_filename

                    type_json = type_yaml = type_longform = markdown_lambda(
                        subproperty_filename, propname
                    )

                    # potential circular ref
                    # setting up markdown before going deep in the heap
                    # to reuse markdown
                    self._marked_down_properties[propname] = {
                        jsontype: type_json,
                        yamltype: type_json,
                        longformtype: type_json,
                    }

                    prop["properties"] = {
                        name: self._set_docs_properties(name, value, proppath + (name,))
                        for name, value in object_properties.items()
                    }

                    LOG.debug(
                        "Writing docs %s: %s", subproperty_filename, subproperty_path
                    )
                    contents = template.render(
                        type_name=self.type_name,
                        subproperty_name=subproperty_name,
                        schema=prop,
                    )

                    self.safewrite(subproperty_path, contents)

            prop[jsontype] = __join(prop.get(jsontype), type_json)
            prop[yamltype] = __join(prop.get(yamltype), type_yaml)
            prop[longformtype] = __join(prop.get(longformtype), type_longform)
            if "enum" in prop:
                prop["allowedvalues"] = prop["enum"]

        prop_type = prop.get("type", "object")

        single_item = False
        if not isinstance(prop_type, list):
            prop_type = [prop_type]
            single_item = True

        for prop_item in prop_type:
            if isinstance(prop_item, tuple):  # if tuple, then it's a ref
                # using doc method to generate the mdo and reassign the ref
                resolved = self._set_docs_properties(
                    propname, {"$ref": prop_item}, proppath
                )
                prop[jsontype] = __join(prop.get(jsontype), resolved[jsontype])
                prop[yamltype] = __join(prop.get(yamltype), resolved[yamltype])
                prop[longformtype] = __join(
                    prop.get(longformtype), resolved[longformtype]
                )
            else:
                __set_property_type(prop_item, single_type=single_item)
        return prop

    def _upload(
        self, fileobj, endpoint_url, region_name, role_arn, use_role, set_default
    ):  # pylint: disable=too-many-arguments, too-many-locals
        LOG.debug("Packaging complete, uploading...")
        session = create_sdk_session(region_name)
        LOG.debug("Uploading to region '%s'", session.region_name)
        cfn_client = session.client("cloudformation", endpoint_url=endpoint_url)
        s3_client = session.client("s3")
        uploader = Uploader(cfn_client, s3_client)
        if use_role and not role_arn and "handlers" in self.schema:
            LOG.debug("Creating execution role for provider to use")
            role_arn = uploader.create_or_update_role(
                self.root / ROLE_TEMPLATE_FILENAME, self.hypenated_name
            )

        s3_url = uploader.upload(self.hypenated_name, fileobj)
        LOG.debug("Got S3 URL: %s", s3_url)
        log_delivery_role = uploader.get_log_delivery_role_arn()
        LOG.debug("Got Log Role: %s", log_delivery_role)
        kwargs = {
            "Type": self.artifact_type,
            "TypeName": self.type_name,
            "SchemaHandlerPackage": s3_url,
            "ClientRequestToken": str(uuid4()),
            "LoggingConfig": {
                "LogRoleArn": log_delivery_role,
                "LogGroupName": "{}-logs".format(self.hypenated_name),
            },
        }
        if role_arn and use_role:
            kwargs["ExecutionRoleArn"] = role_arn

        try:
            response = cfn_client.register_type(**kwargs)

        except ClientError as e:
            LOG.debug("Registering type resulted in unknown ClientError", exc_info=e)
            raise DownstreamError("Unknown CloudFormation error") from e
        else:
            self._wait_for_registration(
                cfn_client, response["RegistrationToken"], set_default
            )

    @staticmethod
    def _wait_for_registration(cfn_client, registration_token, set_default):
        registration_waiter = cfn_client.get_waiter("type_registration_complete")
        try:
            LOG.warning(
                "Successfully submitted type. "
                "Waiting for registration with token '%s' to complete.",
                registration_token,
            )
            registration_waiter.wait(RegistrationToken=registration_token)
        except WaiterError as e:
            LOG.warning(
                "Failed to register the type with registration token '%s'.",
                registration_token,
            )
            try:
                response = cfn_client.describe_type_registration(
                    RegistrationToken=registration_token
                )
            except ClientError as describe_error:
                LOG.debug(
                    "Describing type registration resulted in unknown ClientError",
                    exc_info=e,
                )
                raise DownstreamError(
                    "Error describing type registration"
                ) from describe_error
            LOG.warning(
                "Please see response for additional information: '%s'", response
            )
            raise DownstreamError("Type registration error") from e
        LOG.warning("Registration complete.")
        response = cfn_client.describe_type_registration(
            RegistrationToken=registration_token
        )
        LOG.warning(response)
        if set_default:
            arn = response["TypeVersionArn"]
            try:
                cfn_client.set_type_default_version(Arn=arn)
            except ClientError as e:
                LOG.debug(
                    "Setting default version resulted in unknown ClientError",
                    exc_info=e,
                )
                raise DownstreamError("Error setting default version") from e
            LOG.warning("Set default version to '%s", arn)
