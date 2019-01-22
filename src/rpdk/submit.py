"""This sub command sets up infrastructure and uploads the resource handler.
"""
import logging

from .project import Project

LOG = logging.getLogger(__name__)


def submit(args):
    project = Project()
    project.load()
    project.submit(args.only_package)


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("submit", description=__doc__, parents=parents)
    parser.set_defaults(command=submit)
    parser.add_argument(
        "--only-package",
        default=None,
        help="Skips registering the resource type.",
        action="store_true",
    )
