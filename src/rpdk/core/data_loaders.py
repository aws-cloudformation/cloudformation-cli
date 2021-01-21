import json
import logging
import os
import shutil
from io import TextIOWrapper
from pathlib import Path

import pkg_resources
import yaml
from jsonschema import Draft7Validator, RefResolver
from jsonschema.exceptions import RefResolutionError, ValidationError

from .exceptions import InternalError, SpecValidationError
from .jsonutils.inliner import RefInliner

LOG = logging.getLogger(__name__)

TIMEOUT_IN_SECONDS = 10
STDIN_NAME = "<stdin>"


def resource_stream(package_name, resource_name, encoding="utf-8"):
    """Load a package resource as a decoded file-like object.

    By default, package resources are loaded as binary files, which isn't a
    use-case for us.

    Decoding errors raise :exc:`ValueError`. :term:`universal newlines`
    are enabled. Can be used in a ``with`` statement.
    """
    f = pkg_resources.resource_stream(package_name, resource_name)
    return TextIOWrapper(f, encoding=encoding)


def resource_json(package_name, resource_name):
    """Load a JSON package resource and return the parsed object."""
    with resource_stream(package_name, resource_name) as f:
        return json.load(f)


def resource_yaml(package_name, resource_name):
    """Load a YAML package resource and return the parsed object."""
    with resource_stream(package_name, resource_name) as f:
        return yaml.safe_load(f)


def copy_resource(package_name, resource_name, out_path):
    with pkg_resources.resource_stream(
        package_name, resource_name
    ) as fsrc, out_path.open("wb") as fdst:
        shutil.copyfileobj(fsrc, fdst)


def make_validator(schema, base_uri=None):
    if not base_uri:
        base_uri = Draft7Validator.ID_OF(schema)

    def get_from_local(uri):  # pylint: disable=unused-argument
        meta_schema = Path(os.path.dirname(os.path.realpath(__file__))).joinpath(
            "data/schema/meta-schema.json"
        )
        return json.load(meta_schema.open())

    resolver = RefResolver(
        base_uri=base_uri,
        referrer=schema,
        handlers={"http": get_from_local, "https": get_from_local},
    )
    return Draft7Validator(schema, resolver=resolver)


def make_resource_validator():
    schema = resource_json(__name__, "data/schema/provider.definition.schema.v1.json")
    return make_validator(schema)


def make_resource_validator_with_additional_properties_check():
    schema = resource_json(__name__, "data/schema/provider.definition.schema.v1.json")
    dependencies = schema["definitions"]["validations"]["dependencies"]
    properties_check = {
        "properties": {
            "$comment": "An object cannot have both defined and undefined \
properties; therefore, patternProperties is not allowed when properties is specified.\
 Provider should mark additionalProperties as false if the \
property is of object type and has properties defined \
in it.",
            "not": {"required": ["patternProperties"]},
            "required": ["additionalProperties"],
        }
    }
    pattern_properties_check = {
        "patternProperties": {
            "$comment": "An object cannot have both defined and undefined \
properties; therefore, properties is not allowed when patternProperties is specified. \
Provider should mark additionalProperties as false if the property is of object type \
and has patternProperties defined in it.",
            "not": {"required": ["properties"]},
            "required": ["additionalProperties"],
        }
    }
    schema["definitions"]["validations"]["dependencies"] = {
        **dependencies,
        **properties_check,
        **pattern_properties_check,
    }
    return make_validator(schema)


def get_file_base_uri(file):
    try:
        name = file.name
    except AttributeError:
        LOG.error(
            "Resource spec has no filename associated, "
            "relative references may not work"
        )
        name = STDIN_NAME

    if name == STDIN_NAME:
        path = Path.cwd() / "-"  # fake file
    else:
        path = Path(name)
    return path.resolve().as_uri()


def load_resource_spec(resource_spec_file):  # pylint: disable=R0912 # noqa: C901
    """Load a resource provider definition from a file, and validate it."""
    try:
        resource_spec = json.load(resource_spec_file)
    except ValueError as e:
        LOG.debug("Resource spec decode failed", exc_info=True)
        raise SpecValidationError(str(e)) from e

    validator = make_resource_validator()
    additional_properties_validator = (
        make_resource_validator_with_additional_properties_check()
    )
    try:
        validator.validate(resource_spec)
    except ValidationError as e:
        LOG.debug("Resource spec validation failed", exc_info=True)
        raise SpecValidationError(str(e)) from e

    list_options = {
        "maxresults",
        "maxrecords",
        "maxitems",
        "nexttoken",
        "nextmarker",
        "nextpagetoken",
        "pagetoken",
        "paginationtoken",
    } & set(map(str.lower, resource_spec.get("properties", [])))
    if list_options:
        LOG.warning(
            "LIST API inputs like MaxResults, MaxRecords, MaxItems, NextToken, NextMarker, NextPageToken, PageToken, and Filters are not resource properties. \
%s should not be present in resource schema",
            list_options,
        )

    read_only_properties_intersection = set(
        resource_spec.get("readOnlyProperties", [])
    ) & (
        set(resource_spec.get("createOnlyProperties", []))
        | set(resource_spec.get("writeOnlyProperties", []))
        | {"/properties/" + s for s in resource_spec.get("required", [])}
    )
    if read_only_properties_intersection:
        LOG.warning(
            "readOnlyProperties cannot be specified by customers and should not overlap with writeOnlyProperties, createOnlyProperties, or required: %s",
            read_only_properties_intersection,
        )

    for handler in resource_spec.get("handlers", []):
        for permission in resource_spec.get("handlers", [])[handler]["permissions"]:
            if "*" in permission:
                LOG.warning(
                    "Use specific handler permissions instead of using wildcards: %s",
                    permission,
                )

    try:
        additional_properties_validator.validate(resource_spec)
    except ValidationError as e:
        LOG.warning(
            "[Warning] Resource spec validation would fail from next \
major version. Provider should mark additionalProperties as false if the \
property is of object type and has properties or patternProperties defined \
in it. Please fix the warnings: %s",
            str(e),
        )

    for primary_id in resource_spec["primaryIdentifier"]:
        if primary_id not in resource_spec.get(
            "readOnlyProperties", []
        ) and primary_id not in resource_spec.get("createOnlyProperties", []):
            LOG.warning(
                "Property 'primaryIdentifier' - %s must be specified \
as either readOnly or createOnly",
                primary_id,
            )

    # TODO: more general validation framework
    if "remote" in resource_spec:
        raise SpecValidationError(
            "Property 'remote' is reserved for CloudFormation use"
        )

    try:
        base_uri = resource_spec["$id"]
    except KeyError:
        base_uri = get_file_base_uri(resource_spec_file)

    inliner = RefInliner(base_uri, resource_spec)
    try:
        inlined = inliner.inline()
    except RefResolutionError as e:
        LOG.debug("Resource spec validation failed", exc_info=True)
        raise SpecValidationError(str(e)) from e

    try:
        validator.validate(inlined)
    except ValidationError as e:
        LOG.debug("Inlined schema is no longer valid", exc_info=True)
        raise InternalError() from e

    return inlined
