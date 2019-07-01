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
from .data_loaders import copy_resource
from .project import Project

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


def test(args):
    project = Project()
    project.load()

    plugin = ContractPlugin(
        args.function_name, args.endpoint, args.region, project.schema
    )

    with temporary_ini_file() as path:
        pytest_args = ["-c", path]
        if args.test_types:
            pytest_args.extend(["-k", args.test_types])
        if args.collect_only:
            pytest_args.append("--collect-only")
        pytest.main(pytest_args, plugins=[plugin])


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("test", description=__doc__, parents=parents)
    parser.set_defaults(command=test)

    endpoint = "http://127.0.0.1:3001"
    parser.add_argument(
        "--endpoint",
        default=endpoint,
        help="The endpoint at which the type can be invoked (Default: {})".format(
            endpoint
        ),
    )
    function_name = "TestEntrypoint"
    parser.add_argument(
        "--function-name",
        default=function_name,
        help=(
            "The logical lambda function name in the SAM template (Default: {})"
        ).format(function_name),
    )
    region = "us-east-1"
    parser.add_argument(
        "--region",
        default=region,
        help="The region used for temporary credentials. (Default: {})".format(region),
    )
    parser.add_argument("--test-types", default=None, help=SUPPRESS)
    parser.add_argument("--collect-only", action="store_true", help=SUPPRESS)
