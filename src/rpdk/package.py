"""This sub command sets up infrastructure and uploads the resource handler.
"""
import logging

from .project import Project

LOG = logging.getLogger(__name__)


def package(_args):
    project = Project()
    project.load()
    project.package()


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("package", description=__doc__, parents=parents)
    parser.set_defaults(command=package)
