"""This sub command validates a project's resource specification.

Projects can be created via the 'init' sub command.
"""
import logging

from .project import Project

LOG = logging.getLogger(__name__)


def validate(_args):
    project = Project()
    project.load()
    LOG.info("Resource specification is valid.")


def setup_subparser(subparsers, parents):
    parser = subparsers.add_parser("validate", description=__doc__, parents=parents)
    parser.set_defaults(command=validate)
