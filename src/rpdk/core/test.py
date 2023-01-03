"""This sub command tests basic functionality of the resource in the project.

Projects can be created via the 'init' sub command.
"""
import json
import logging
import os
from argparse import SUPPRESS
from collections import OrderedDict
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from jinja2 import Environment, Template, meta
from jsonschema import Draft6Validator
from jsonschema.exceptions import ValidationError

from rpdk.core.contract.hook_client import HookClient
from rpdk.core.jsonutils.pointer import fragment_decode
from rpdk.core.utils.handler_utils import generate_handler_name

from .boto_helpers import create_sdk_session, get_temporary_credentials
from .contract.contract_plugin import ContractPlugin
from .contract.interface import Action, HookInvocationPoint
from .contract.resource_client import ResourceClient
from .data_loaders import copy_resource
from .exceptions import SysExitRecommendedError
from .project import ARTIFACT_TYPE_HOOK, ARTIFACT_TYPE_MODULE, Project

LOG = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "http://127.0.0.1:3001"
DEFAULT_FUNCTION = "TypeFunction"
DEFAULT_REGION = "us-east-1"
DEFAULT_TIMEOUT = "240"
INPUTS = "inputs"

RESOURCE_OVERRIDES_VALIDATOR = Draft6Validator(
    {
        "properties": {"CREATE": {"type": "object"}, "UPDATE": {"type": "object"}},
        "anyOf": [{"required": ["CREATE"]}, {"required": ["UPDATE"]}],
        "additionalProperties": False,
    }
)

HOOK_OVERRIDES_VALIDATOR = Draft6Validator(
    {
        "properties": {
            "CREATE_PRE_PROVISION": {"type": "object"},
            "UPDATE_PRE_PROVISION": {"type": "object"},
            "DELETE_PRE_PROVISION": {"type": "object"},
            "INVALID_CREATE_PRE_PROVISION": {"type": "object"},
            "INVALID_UPDATE_PRE_PROVISION": {"type": "object"},
            "INVALID_DELETE_PRE_PROVISION": {"type": "object"},
            "INVALID": {"type": "object"},
        },
        "anyOf": [
            {"required": ["CREATE_PRE_PROVISION"]},
            {"required": ["UPDATE_PRE_PROVISION"]},
            {"required": ["DELETE_PRE_PROVISION"]},
            {"required": ["INVALID_CREATE_PRE_PROVISION"]},
            {"required": ["INVALID_UPDATE_PRE_PROVISION"]},
            {"required": ["INVALID_DELETE_PRE_PROVISION"]},
            {"required": ["INVALID"]},
        ],
        "additionalProperties": False,
    }
)


def empty_override():
    return {"CREATE": {}}


def empty_hook_override():
    return {"CREATE_PRE_PROVISION": {}}


# As per Python docs NamedTemporaryFile does NOT work the same in Windows.  Setting delete=False as workaround.
#
# Temporary file must be explicitly cleaned up after temporary_ini_file() is called!
#
# "Whether the name can be used to open the file a second time, while the named temporary file is still open,
# varies across platforms (it can be so used on Unix; it cannot on Windows)."
# https://docs.python.org/3.9/library/tempfile.html#tempfile.NamedTemporaryFile
#
# Fix being tracked here https://github.com/python/cpython/issues/58451


@contextmanager
def temporary_ini_file():
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="pytest_", suffix=".ini", delete=False
    ) as temp:
        LOG.debug("temporary pytest.ini path: %s", temp.name)
        path = Path(temp.name).resolve(strict=True)
        copy_resource(__name__, "data/pytest-contract.ini", path)
        # Close temporary file for other processes to use, needed on Windows
        temp.close()
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


def filter_overrides(overrides, project):
    if project.artifact_type == ARTIFACT_TYPE_HOOK:
        actions = set(HookInvocationPoint)
    else:
        actions = set(Action)

    for k in set(overrides) - actions:
        del overrides[k]

    return overrides


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
        RESOURCE_OVERRIDES_VALIDATOR.validate(overrides_raw)
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
# flake8: noqa: C901
def get_hook_overrides(root, region_name, endpoint_url, role_arn):
    if not root:
        return empty_hook_override()

    path = root / "overrides.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            overrides_raw = render_jinja(f.read(), region_name, endpoint_url, role_arn)
    except FileNotFoundError:
        LOG.debug("Override file '%s' not found. No overrides will be applied", path)
        return empty_hook_override()

    try:
        HOOK_OVERRIDES_VALIDATOR.validate(overrides_raw)
    except ValidationError as e:
        LOG.warning("Override file invalid: %s\n" "No overrides will be applied", e)
        return empty_hook_override()

    overrides = empty_hook_override()
    for (
        operation,
        operation_items_raw,
    ) in overrides_raw.items():  # Hook invocation point (e.g. CREATE_PRE_PROVISION)
        operation_items = {}
        for (
            target_name,
            target_items_raw,
        ) in operation_items_raw.items():  # Hook targets (e.g. AWS::S3::Bucket)
            target_items = {}
            for (
                item,
                items_raw,
            ) in (
                target_items_raw.items()
            ):  # Target Model fields (e.g. 'resourceProperties', 'previousResourceProperties')
                items = {}
                for pointer, obj in items_raw.items():
                    try:
                        pointer = fragment_decode(pointer, prefix="")
                    except ValueError:  # pragma: no cover
                        LOG.warning(
                            "%s pointer '%s' is invalid. Skipping", operation, pointer
                        )
                    else:
                        items[pointer] = obj
                target_items[item] = items
            operation_items[target_name] = target_items
        overrides[operation] = operation_items

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


# pylint: disable=too-many-return-statements
def get_type(file_name):
    if "invalid_pre_create" in file_name:
        return "INVALID_CREATE_PRE_PROVISION"
    if "invalid_pre_update" in file_name:
        return "INVALID_UPDATE_PRE_PROVISION"
    if "invalid_pre_delete" in file_name:
        return "INVALID_DELETE_PRE_PROVISION"
    if "pre_create" in file_name:
        return "CREATE_PRE_PROVISION"
    if "pre_update" in file_name:
        return "UPDATE_PRE_PROVISION"
    if "pre_delete" in file_name:
        return "DELETE_PRE_PROVISION"
    if "create" in file_name:
        return "CREATE"
    if "update" in file_name:
        return "UPDATE"
    if "invalid" in file_name:
        return "INVALID"
    return None


def get_resource_marker_options(schema):
    lowercase_actions = [action.lower() for action in Action]
    handlers = schema.get("handlers", {}).keys()
    return [action for action in lowercase_actions if action not in handlers]


def get_hook_marker_options(schema):
    handlers = schema.get("handlers", {}).keys()
    action_to_handler = OrderedDict()
    for invocation_point in HookInvocationPoint:
        handler_name = generate_handler_name(invocation_point)
        action_to_handler[handler_name] = invocation_point.lower()

    excluded_actions = [
        action for action in action_to_handler.keys() if action not in handlers
    ]
    return [action_to_handler[excluded_action] for excluded_action in excluded_actions]


def get_marker_options(schema):
    excluded_actions = get_resource_marker_options(schema) + get_hook_marker_options(
        schema
    )
    marker_list = ["not " + action for action in excluded_actions]
    return " and ".join(marker_list)


def get_contract_plugin_client(args, project, overrides, inputs):
    plugin_clients = {}
    if project.artifact_type == ARTIFACT_TYPE_HOOK:
        plugin_clients["hook_client"] = HookClient(
            args.function_name,
            args.endpoint,
            args.region,
            project.schema,
            overrides,
            inputs,
            args.role_arn,
            args.enforce_timeout,
            project.type_name,
            args.log_group_name,
            args.log_role_arn,
            executable_entrypoint=project.executable_entrypoint,
            docker_image=args.docker_image,
            target_info=project._load_target_info(  # pylint: disable=protected-access
                args.cloudformation_endpoint_url, args.region
            ),
        )
        LOG.debug("Setup plugin for HOOK type")
        return plugin_clients

    plugin_clients["resource_client"] = ResourceClient(
        args.function_name,
        args.endpoint,
        args.region,
        project.schema,
        overrides,
        inputs,
        args.role_arn,
        args.enforce_timeout,
        project.type_name,
        args.log_group_name,
        args.log_role_arn,
        executable_entrypoint=project.executable_entrypoint,
        docker_image=args.docker_image,
    )
    LOG.debug("Setup plugin for RESOURCE type")
    return plugin_clients


def test(args):
    _validate_sam_args(args)
    project = Project()
    project.load()
    if project.artifact_type == ARTIFACT_TYPE_MODULE:
        LOG.warning("The test command is not supported in a module project")
        return

    if project.artifact_type == ARTIFACT_TYPE_HOOK:
        overrides = get_hook_overrides(
            project.root, args.region, args.cloudformation_endpoint_url, args.role_arn
        )
    else:
        overrides = get_overrides(
            project.root, args.region, args.cloudformation_endpoint_url, args.role_arn
        )
        filter_overrides(overrides, project)

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
    plugin_clients = get_contract_plugin_client(args, project, overrides, inputs)
    plugin = ContractPlugin(plugin_clients)
    with temporary_ini_file() as path:
        pytest_args = ["-c", path, "-m", get_marker_options(project.schema)]
        if args.passed_to_pytest:
            LOG.debug("extra args: %s", args.passed_to_pytest)
            pytest_args.extend(args.passed_to_pytest)
        LOG.debug("pytest args: %s", pytest_args)
        ret = pytest.main(pytest_args, plugins=[plugin])
        # Manually clean up temporary file before exiting - issue with NamedTemporaryFile method on Windows
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
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

    parser.add_argument(
        "--log-group-name",
        help="The log group to which contract tests lambda handler logs will be delivered. "
        "Specified log group doesn't have to exist as long as log-role-arn specified has logs:CreateLogGroup "
        "permission. Need to be used together with --log-role-arn",
    )

    parser.add_argument(
        "--log-role-arn",
        help="Role for delivering contract tests lambda handler logs. Need to be used together with --log-group-name",
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
