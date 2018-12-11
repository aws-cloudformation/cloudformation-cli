"""This sub command generates IDE and build files for a given language.
"""
import logging

from .project import Project

LOG = logging.getLogger(__name__)


def init(args):
    project = Project(args.force)

    LOG.warning("Initializing new project")

    project.init("AWS::Color::Red", "java")
    project.load_schema()
    project.generate()


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("init", description=__doc__, parents=parents)
    parser.set_defaults(command=init)

    parser.add_argument(
        "--force", action="store_true", help="Force files to be overwritten."
    )
