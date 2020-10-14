"""This sub command adds credentials to a payload, and sends it to a Lambda
function. The function is re-invoked while the IN_PROGRESS status is returned.

Projects can be created via the 'init' sub command.
"""
# pylint: disable=protected-access
import json
import logging
from argparse import FileType
from time import sleep

from .contract.interface import Action, OperationStatus
from .contract.resource_client import ResourceClient
from .exceptions import SysExitRecommendedError
from .project import Project
from .test import _sam_arguments, _validate_sam_args

LOG = logging.getLogger(__name__)


def invoke(args):
    _validate_sam_args(args)
    project = Project()
    project.load()

    client = ResourceClient(
        args.function_name,
        args.endpoint,
        args.region,
        project.schema,
        {},
        executable_entrypoint=project.executable_entrypoint,
        docker_image=args.docker_image,
    )

    action = Action[args.action]
    try:
        request = json.load(args.request)
    except ValueError as e:
        raise SysExitRecommendedError(f"Invalid JSON: {e}") from e
    payload = client._make_payload(
        action, request["desiredResourceState"], request["previousResourceState"]
    )

    current_invocation = 0

    try:
        while _needs_reinvocation(args.max_reinvoke, current_invocation):
            print("=== Handler input ===")
            print(json.dumps({**payload, "credentials": "<redacted>"}, indent=2))
            response = client._call(payload)
            current_invocation = current_invocation + 1
            print("=== Handler response ===")
            print(json.dumps(response, indent=2))
            status = OperationStatus[response["status"]]

            if status != OperationStatus.IN_PROGRESS:
                break

            sleep(response.get("callbackDelaySeconds", 0))
            payload["callbackContext"] = response.get("callbackContext")
    except KeyboardInterrupt:
        pass


def _needs_reinvocation(max_reinvoke, current_invocation):
    return max_reinvoke is None or max_reinvoke >= current_invocation


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("invoke", description=__doc__, parents=parents)
    parser.set_defaults(command=invoke)
    parser.add_argument(
        "action",
        choices=list(Action.__members__),
        help="The provisioning action, i.e. which handler to invoke.",
    )
    parser.add_argument(
        "request",
        type=FileType("r", encoding="utf-8"),
        help="A JSON file that contains the request to invoke the function with.",
    )
    parser.add_argument(
        "--max-reinvoke",
        type=int,
        default=None,
        help="Maximum number of IN_PROGRESS re-invocations allowed before "
        "exiting. If not specified, will continue to "
        "re-invoke until terminal status is reached.",
    )
    parser.add_argument(
        "--docker-image",
        help="Docker image name to run. If specified, invoke will use docker instead "
        "of SAM",
    )
    _sam_arguments(parser)
