"""This tool auto-generated resource providers given a specification."""
import argparse
from logging.config import dictConfig

import pkg_resources
import yaml

from .generate import setup_subparser as generate_setup_subparser


def main():
    logging_config = yaml.safe_load(pkg_resources.resource_stream(
        __name__, 'data/logging.yaml'))
    dictConfig(logging_config)

    # see docstring of this file
    parser = argparse.ArgumentParser(description=__doc__)

    # the default command just prints the help message
    # subparsers should set their own default commands
    parser.set_defaults(command=lambda args: parser.print_help())

    subparsers = parser.add_subparsers(dest='subparser_name')
    generate_setup_subparser(subparsers)

    args = parser.parse_args()
    args.command(args)


if __name__ == '__main__':
    main()
