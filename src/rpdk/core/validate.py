"""This sub command validates a project's resource schema.

Projects can be created via the 'init' sub command.
"""
import logging

from .project import Project

LOG = logging.getLogger(__name__)


# validations for cfn validate are done in both project.py and data_loaders.py
def validate(_args):
    project = Project()
    project.load()


def setup_subparser(subparsers, parents):
    parser = subparsers.add_parser("validate", description=__doc__, parents=parents)
    parser.set_defaults(command=validate)
