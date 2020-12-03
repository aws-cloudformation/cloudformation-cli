"""This sub command tests basic functionality of the resource in the project.

Projects can be created via the 'init' sub command.
"""
import json
import logging
import os
from argparse import SUPPRESS
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from jinja2 import Environment, Template, meta
from jsonschema import Draft6Validator
from jsonschema.exceptions import ValidationError

from rpdk.core.jsonutils.pointer import fragment_decode

from .boto_helpers import create_sdk_session, get_temporary_credentials
from .contract.contract_plugin import ContractPlugin
from .contract.interface import Action
from .contract.resource_client import ResourceClient
from .data_loaders import copy_resource
from .exceptions import SysExitRecommendedError
from .project import ARTIFACT_TYPE_MODULE, Project

LOG = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "http://127.0.0.1:3001"
DEFAULT_FUNCTION = "TypeFunction"
DEFAULT_REGION = "us-east-1"
DEFAULT_TIMEOUT = "30"
INPUTS = "inputs"

OVERRIDES_VALIDATOR = Draft6Validator(
    {
        "properties": {"CREATE": {"type": "object"}, "UPDATE": {"type": "object"}},
        "anyOf": [{"required": ["CREATE"]}, {"required": ["UPDATE"]}],
        "additionalProperties": False,
    }
)


def empty_override():
    return {"CREATE": {}}


@contextmanager
def temporary_ini_file():
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="pytest_", suffix=".ini"
    ) as temp:
        LOG.debug("temporary pytest.ini path: %s", temp.name)
        path = Path(temp.name).resolve(strict=True)
        copy_resource(__name__, "data/pytest-contract.ini", path)
        yield str(path)


def get_cloudformation_exports(region_name, endpoint_url, role_arn):
    session = create_sdk_session(region_name)
    temp_credentials = get_temporary_credentials(session, role_arn=role_arn)
    cfn_client = session.client(
        "cloudformation", endpoint_url=endpoint_url, **temp_credentials
    )
    paginator = cfn_client.get_paginator("list_exports")
    pages = paginator.paginate()
    exports = {}
    for page in pages:
        exports.update({export["Name"]: export["Value"] for export in page["Exports"]})
    return exports


def render_jinja(overrides_string, region_name, endpoint_url, role_arn):
    env = Environment(autoescape=True)
    parsed_content = env.parse(overrides_string)
    variables = meta.find_undeclared_variables(parsed_content)
    if variables:
        exports = get_cloudformation_exports(region_name, endpoint_url, role_arn)
        invalid_exports = variables - exports.keys()
        if len(invalid_exports) > 0:
            invalid_exports_message = (
                "Override file invalid: %s are not valid cloudformation exports."
                + "No Overrides will be applied"
            )
            LOG.warning(invalid_exports_message, invalid_exports)
            return empty_override()
        overrides_template = Template(overrides_string)
        to_return = json.loads(overrides_template.render(exports))
    else:
        to_return = json.loads(overrides_string)
    return to_return


def get_overrides(root, region_name, endpoint_url, role_arn):
    if not root:
        return empty_override()

    path = root / "overrides.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            overrides_raw = render_jinja(f.read(), region_name, endpoint_url, role_arn)
    except FileNotFoundError:
        LOG.debug("Override file '%s' not found. No overrides will be applied", path)
        return empty_override()

    try:
        OVERRIDES_VALIDATOR.validate(overrides_raw)
    except ValidationError as e:
        LOG.warning("Override file invalid: %s\n" "No overrides will be applied", e)
        return empty_override()

    overrides = empty_override()
    for operation, items_raw in overrides_raw.items():
        items = {}
        for pointer, obj in items_raw.items():
            try:
                pointer = fragment_decode(pointer, prefix="")
            except ValueError:
                LOG.warning("%s pointer '%s' is invalid. Skipping", operation, pointer)
            else:
                items[pointer] = obj
        overrides[operation] = items

    return overrides


# pylint: disable=R0914
def get_inputs(root, region_name, endpoint_url, value, role_arn):
    inputs = {}
    if not root:
        return None

    path = root / INPUTS
    if not os.path.isdir(path):
        return None

    file_prefix = INPUTS + "_" + str(value)

    directories = os.listdir(path)
    if len(directories) > 0:
        for file in directories:
            if file.startswith(file_prefix) and file.endswith(".json"):
                input_type = get_type(file)
                if not input_type:
                    continue

                file_path = path / file
                with file_path.open("r", encoding="utf-8") as f:
                    overrides_raw = render_jinja(
                        f.read(), region_name, endpoint_url, role_arn
                    )
                overrides = {}
                for pointer, obj in overrides_raw.items():
                    overrides[pointer] = obj
                inputs[input_type] = overrides
        return inputs
    return None


def get_type(file_name):
    if "create" in file_name:
        return "CREATE"
    if "update" in file_name:
        return "UPDATE"
    if "invalid" in file_name:
        return "INVALID"
    return None


def get_marker_options(schema):
    lowercase_actions = {action.lower() for action in Action}
    excluded_actions = lowercase_actions - schema.get("handlers", {}).keys()
    marker_list = ["not " + action for action in excluded_actions]
    return " and ".join(marker_list)


def test(args):
    _validate_sam_args(args)
    project = Project()
    project.load()
    if project.artifact_type == ARTIFACT_TYPE_MODULE:
        LOG.warning("The test command is not supported in a module project")
        return

    overrides = get_overrides(
        project.root, args.region, args.cloudformation_endpoint_url, args.role_arn
    )

    index = 1
    while True:
        inputs = get_inputs(
            project.root,
            args.region,
            args.cloudformation_endpoint_url,
            index,
            args.role_arn,
        )
        if not inputs:
            break
        invoke_test(args, project, overrides, inputs)
        index = index + 1

    if index == 1:
        invoke_test(args, project, overrides, None)


def invoke_test(args, project, overrides, inputs):
    plugin = ContractPlugin(
        ResourceClient(
            args.function_name,
            args.endpoint,
            args.region,
            project.schema,
            overrides,
            inputs,
            args.role_arn,
            args.enforce_timeout,
            executable_entrypoint=project.executable_entrypoint,
            docker_image=args.docker_image,
        )
    )

    with temporary_ini_file() as path:
        pytest_args = ["-c", path, "-m", get_marker_options(project.schema)]
        if args.passed_to_pytest:
            LOG.debug("extra args: %s", args.passed_to_pytest)
            pytest_args.extend(args.passed_to_pytest)
        LOG.debug("pytest args: %s", pytest_args)
        ret = pytest.main(pytest_args, plugins=[plugin])
        if ret:
            raise SysExitRecommendedError("One or more contract tests failed")


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("test", description=__doc__, parents=parents)
    parser.set_defaults(command=test)

    _sam_arguments(parser)
    # this parameter can be used to pass additional arguments to pytest after `--`
    # for example,

    parser.add_argument(
        "--role-arn", help="Role used when performing handler operations."
    )

    parser.add_argument(
        "--cloudformation-endpoint-url", help="CloudFormation endpoint to use."
    )

    parser.add_argument(
        "--enforce-timeout",
        default=DEFAULT_TIMEOUT,
        help="Enforce a different timeout for handlers",
    )

    parser.add_argument("passed_to_pytest", nargs="*", help=SUPPRESS)

    parser.add_argument(
        "--docker-image",
        help="Docker image name to run. If specified, invoke will use docker instead "
        "of SAM",
    )


def _sam_arguments(parser):
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=(
            "The endpoint at which the type can be invoked "
            f"(Default: {DEFAULT_ENDPOINT})"
        ),
    )
    parser.add_argument(
        "--function-name",
        default=DEFAULT_FUNCTION,
        help=(
            "The logical lambda function name in the SAM template "
            f"(Default: {DEFAULT_FUNCTION})"
        ),
    )
    parser.add_argument(
        "--region",
        default=DEFAULT_REGION,
        help=(
            "The region used for temporary credentials " f"(Default: {DEFAULT_REGION})"
        ),
    )


def _validate_sam_args(args):
    if args.docker_image and (
        args.endpoint != DEFAULT_ENDPOINT or args.function_name != DEFAULT_FUNCTION
    ):
        raise SysExitRecommendedError(
            "Cannot specify both --docker-image and --endpoint or --function-name"
        )
