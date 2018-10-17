"""This sub command tests basic functionality of the
 resource handler given a test resource and an endpoint.
"""
import json
import logging

import pytest

from .tests.contract_plugin import ContractPlugin
from .tests.transports import LocalLambdaTransport

LOG = logging.getLogger(__name__)


def local_lambda(args):
    transport = LocalLambdaTransport(args.endpoint, args.function_name)
    with open(args.test_resource) as json_data:
        resource = json.load(json_data)
    plugin = ContractPlugin(transport, resource)
    pytest.main(
        ["--pyargs", "uluru.tests.contract_tests", "-p", "no:warnings"],
        plugins=[plugin],
    )


def setup_subparser(subparsers):
    # see docstring of this file
    parser = subparsers.add_parser("test", description=__doc__)
    test_subparsers = parser.add_subparsers(help="local invocation using SAM CLI")
    local_lambda_subparser = test_subparsers.add_parser("local-lambda")
    local_lambda_subparser.set_defaults(command=local_lambda)

    local_lambda_subparser.add_argument(
        "--endpoint",
        dest="endpoint",
        default="http://127.0.0.1:3001",
        help="The endpoint at which the local lambda service is running",
    )

    local_lambda_subparser.add_argument(
        "--function-name",
        dest="function_name",
        default="Handler",
        help="The logical lambda function name in the SAM template",
    )

    local_lambda_subparser.add_argument(
        "--test-resource",
        dest="test_resource",
        help="Example resource model to be used for testing",
    )
