"""This sub command registers the resource type with the registry service.
"""
import logging

from rpdk.project import Project

LOG = logging.getLogger(__name__)


def submit(_args):
    project = Project()
    project.load()
    project.submit()


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("submit", description=__doc__, parents=parents)
    parser.set_defaults(command=submit)
