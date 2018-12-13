"""This sub command sets up infrastructure and uploads the resource handler.
"""
import logging

from .project import Project

LOG = logging.getLogger(__name__)


def package(_args):
    project = Project()
    try:
        project.load_settings()
    except FileNotFoundError:
        LOG.error("Project file not found. Have you run 'init'?")
        raise SystemExit(1)
    project.package()


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("package", description=__doc__, parents=parents)
    parser.set_defaults(command=package)
    # TODO this should be an optional argument and loaded in by the rpdk config
    # https://github.com/awslabs/aws-cloudformation-rpdk/issues/141
