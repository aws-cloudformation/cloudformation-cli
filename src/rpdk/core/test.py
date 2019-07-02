"""This sub command tests basic functionality of the resource in the project.

Projects can be created via the 'init' sub command.
"""
import logging
from argparse import SUPPRESS
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from .contract.contract_plugin import ContractPlugin
from .contract.resource_client import ResourceClient
from .data_loaders import copy_resource
from .exceptions import SysExitRecommendedError
from .project import Project

LOG = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "http://127.0.0.1:3001"
DEFAULT_FUNCTION = "TestEntrypoint"
DEFAULT_REGION = "us-east-1"


@contextmanager
def temporary_ini_file():
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="pytest_", suffix=".ini"
    ) as temp:
        LOG.debug("temporary pytest.ini path: %s", temp.name)
        path = Path(temp.name).resolve(strict=True)
        copy_resource(__name__, "data/pytest-contract.ini", path)
        yield str(path)


def test(args):
    project = Project()
    project.load()

    plugin = ContractPlugin(
        ResourceClient(args.function_name, args.endpoint, args.region, project.schema)
    )

    with temporary_ini_file() as path:
        pytest_args = ["-c", path]
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

    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help="The endpoint at which the type can be invoked (Default: {})".format(
            DEFAULT_ENDPOINT
        ),
    )
    parser.add_argument(
        "--function-name",
        default=DEFAULT_FUNCTION,
        help=(
            "The logical lambda function name in the SAM template (Default: {})"
        ).format(DEFAULT_FUNCTION),
    )
    parser.add_argument(
        "--region",
        default=DEFAULT_REGION,
        help="The region used for temporary credentials. (Default: {})".format(
            DEFAULT_REGION
        ),
    )
    # this parameter can be used to pass additional arguments to pytest after `--`
    # for example,
    parser.add_argument("passed_to_pytest", nargs="*", help=SUPPRESS)
