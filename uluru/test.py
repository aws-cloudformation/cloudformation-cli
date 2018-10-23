"""This sub command tests basic functionality of the
resource handler given a test resource and an endpoint.
"""
import argparse
import json
import logging

import pytest

from .tests.contract_plugin import ContractPlugin
from .tests.transports import LocalLambdaTransport

LOG = logging.getLogger(__name__)


def local_lambda(args):
    transport = LocalLambdaTransport(args.endpoint, args.function_name)
    resource = json.load(args.resource)
    resource_def = json.load(args.definition)

    pytest_args = [
        "--pyargs",
        "uluru.tests.contract_tests",
        "-p",
        "no:warnings",
        "--verbose",
    ]
    if args.test_types:
        pytest_args.extend(["-k", args.test_types])
    pytest.main(
        pytest_args, plugins=[ContractPlugin(transport, resource, resource_def)]
    )


def setup_subparser(subparsers):
    # see docstring of this file
    parser = subparsers.add_parser("test", description=__doc__)
    test_subparsers = parser.add_subparsers(help="Type of transport to use for testing")
    local_lambda_subparser = test_subparsers.add_parser("local-lambda")
    local_lambda_subparser.set_defaults(command=local_lambda)

    local_lambda_subparser.add_argument(
        "resource", help="Example resource model", type=argparse.FileType("r")
    )

    local_lambda_subparser.add_argument(
        "definition",
        help="The definition of the resource that the handler provisions ",
        type=argparse.FileType("r"),
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

    local_lambda_subparser.add_argument(
        "--test-types", default=None, help="The type of contract tests to be run."
    )
