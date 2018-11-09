"""This sub command tests basic functionality of the
resource handler given a test resource and an endpoint.
"""
import json
import logging
from argparse import SUPPRESS, ArgumentParser
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from .argutils import TextFileType
from .contract.contract_plugin import ContractPlugin
from .contract.transports import LocalLambdaTransport
from .data_loaders import copy_resource

LOG = logging.getLogger(__name__)


@contextmanager
def temporary_ini_file():
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="pytest_", suffix=".ini"
    ) as temp:
        LOG.debug("temporary pytest.ini path: %s", temp.name)
        path = Path(temp.name).resolve(strict=True)
        copy_resource(__name__, "data/pytest-contract.ini", path)
        yield str(path)


def invoke_pytest(transport, args):
    resource_def = json.load(args.resource_def_file)
    resource = json.load(args.resource_file)
    updated_resource = json.load(args.updated_resource_file)

    with temporary_ini_file() as path:
        pytest_args = ["--pyargs", "rpdk.contract.suite", "-c", path]
        if args.test_types:
            pytest_args.extend(["-k", args.test_types])
        if args.collect_only:
            pytest_args.extend(["--collect-only"])
        pytest.main(
            pytest_args,
            plugins=[
                ContractPlugin(transport, resource, updated_resource, resource_def)
            ],
        )


def local_lambda(args):
    transport = LocalLambdaTransport(args.endpoint, args.function_name)
    try:
        transport({"requestContext": {}}, ("", ""))
    except EndpointConnectionError:
        LOG.error(
            "Local Lambda Service endpoint %s could not be reached. "
            "Verify that the local lambda service from SAM CLI is running",
            args.endpoint,
        )
        return
    except ClientError as e:
        if "Function not found" in e.args[0]:
            LOG.error(
                "Function with name '%s' not found running on local lambda service. "
                "Verify that the function name matches "
                "the logical name in the SAM Template. ",
                args.function_name,
            )
            return
        raise
    invoke_pytest(transport, args)


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("test", description=__doc__, parents=parents)
    # need to set this, so the help of this specific subparser is printed,
    # not the parent's help
    parser.set_defaults(command=lambda args: parser.print_help())

    # shared arguments
    pytest_shared = ArgumentParser(add_help=False)
    pytest_shared.add_argument(
        "resource_file", help="Example resource model", type=TextFileType("r")
    )
    pytest_shared.add_argument(
        "updated_resource_file",
        help="Additional resource model to be used in update specific tests",
        type=TextFileType("r"),
    )
    pytest_shared.add_argument(
        "resource_def_file",
        help="The definition of the resource that the handler provisions",
        type=TextFileType("r"),
    )
    pytest_shared.add_argument(
        "--test-types", default=None, help="The type of contract tests to be run."
    )
    pytest_shared.add_argument("--collect-only", action="store_true", help=SUPPRESS)
    pytest_parents = [pytest_shared]

    test_subparsers = parser.add_subparsers(help="Type of transport to use for testing")
    _setup_local_lambda_subparser(test_subparsers, pytest_parents)
    return test_subparsers, pytest_parents


def _setup_local_lambda_subparser(test_subparsers, pytest_parents):
    local_lambda_subparser = test_subparsers.add_parser(
        "local-lambda", parents=pytest_parents
    )
    local_lambda_subparser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:3001",
        help="The endpoint at which the handler can be invoked",
    )
    local_lambda_subparser.add_argument(
        "--function-name",
        default="Handler",
        help="The logical lambda function name in the SAM template",
    )
    local_lambda_subparser.set_defaults(command=local_lambda)
