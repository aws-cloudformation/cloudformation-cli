"""This sub command sets up infrastructure and uploads the resource handler
"""
import logging

from .plugin_registry import add_language_argument, get_plugin

LOG = logging.getLogger(__name__)


def package(args):
    plugin = get_plugin(args.language)
    plugin.package(args.handler_path)


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("package", description=__doc__, parents=parents)
    parser.set_defaults(command=package)
    parser.add_argument("handler_path", help="The file path of the handler zip file")
    add_language_argument(parser)
