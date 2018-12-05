"""This sub command generates code from the provider definition for a project.

Projects can be created via the 'init' sub command.
"""
import logging

from jsonschema.exceptions import ValidationError

from .project import Project

LOG = logging.getLogger(__name__)


def generate(_args):
    project = Project()
    try:
        project.load_settings()
    except FileNotFoundError:
        LOG.error("Project file not found. Have you run 'init'?")
        raise SystemExit(1)

    try:
        project.load_schema()
    except FileNotFoundError:
        LOG.error("Resource specification not found.")
        raise SystemExit(1)
    except ValidationError:
        LOG.error("Resource specification is invalid.")
        raise SystemExit(1)

    project.generate()


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("generate", description=__doc__, parents=parents)
    parser.set_defaults(command=generate)
