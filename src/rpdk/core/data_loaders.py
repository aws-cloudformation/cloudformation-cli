import json
import logging
import shutil
from io import TextIOWrapper
from pathlib import Path

import pkg_resources
import requests
import yaml
from jsonschema import Draft7Validator, RefResolver
from jsonschema.exceptions import ValidationError

from .jsonutils.inliner import RefInliner

LOG = logging.getLogger(__name__)


class InternalError(Exception):
    pass


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


def make_validator(schema, base_uri=None, timeout=TIMEOUT_IN_SECONDS):
    if not base_uri:
        base_uri = Draft7Validator.ID_OF(schema)

    def get_with_timeout(uri):
        return requests.get(uri, timeout=timeout).json()

    resolver = RefResolver(
        base_uri=base_uri,
        referrer=schema,
        handlers={"http": get_with_timeout, "https": get_with_timeout},
    )
    return Draft7Validator(schema, resolver=resolver)


def make_resource_validator(base_uri=None, timeout=TIMEOUT_IN_SECONDS):
    schema = resource_json(__name__, "data/schema/provider.definition.schema.v1.json")
    return make_validator(schema, base_uri=base_uri, timeout=timeout)


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


def load_resource_spec(resource_spec_file):
    """Load a resource provider definition from a file, and validate it."""
    try:
        resource_spec = yaml.safe_load(resource_spec_file)
    except yaml.YAMLError as e:
        LOG.error("Could not load the resource provider definition: %s", e)
        raise
        # TODO: error handling, decode errors have 'msg', 'doc', 'pos'

    validator = make_resource_validator()
    try:
        validator.validate(resource_spec)
    except ValidationError as e:
        LOG.error(
            "The resource provider definition is invalid: %s", e.message  # noqa: B306
        )
        raise

    # TODO: more general validation framework
    if "remote" in resource_spec:
        raise ValidationError(
            message="Property 'remote' is reserved for CloudFormation use",
            validator="cloudFormation",
            validator_value=False,
            instance=resource_spec,
            schema=resource_spec,
        )

    base_uri = get_file_base_uri(resource_spec_file)

    inliner = RefInliner(base_uri, resource_spec)
    inlined = inliner.inline()

    try:
        validator.validate(inlined)
    except ValidationError as e:
        LOG.debug("Inlined schema is no longer valid", exc_info=True)
        raise InternalError() from e

    return inlined
