"""This tool provides support for creating CloudFormation resource providers.
"""
import argparse
import logging
from logging.config import dictConfig

import pkg_resources
import yaml

from .generate import setup_subparser as generate_setup_subparser
from .init import setup_subparser as init_setup_subparser
from .project_settings import setup_subparser as project_settings_setup_subparser
from .validate import setup_subparser as validate_setup_subparser


def setup_logging(verbosity=0):
    if verbosity > 1:
        level = logging.DEBUG
    elif verbosity > 0:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging_config = yaml.safe_load(
        pkg_resources.resource_stream(__name__, "data/logging/logging.yaml")
    )
    logging_config["handlers"]["console"]["level"] = level
    dictConfig(logging_config)


def main():
    # see docstring of this file
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase the output verbosity. Can be specified multiple times.",
    )

    # the default command just prints the help message
    # subparsers should set their own default commands
    parser.set_defaults(command=lambda args: parser.print_help())

    subparsers = parser.add_subparsers(dest="subparser_name")
    init_setup_subparser(subparsers)
    validate_setup_subparser(subparsers)
    generate_setup_subparser(subparsers)
    project_settings_setup_subparser(subparsers)

    args = parser.parse_args()

    setup_logging(args.verbose)
    args.command(args)


if __name__ == "__main__":
    main()
