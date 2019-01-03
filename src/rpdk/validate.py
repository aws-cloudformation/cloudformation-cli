"""This sub command validates a resource provider definition."""
import logging

from jsonschema.exceptions import ValidationError

from .project import Project

LOG = logging.getLogger(__name__)


def validate(_args):
    project = Project()
    try:
        project.load_settings()
    except FileNotFoundError:
        LOG.error("Project file not found. Have you run 'init'?")
        raise SystemExit(1)

    LOG.info("Validating your resource specification...")
    try:
        project.load_schema()
    except ValidationError:
        LOG.error("Resource specification is invalid.")
        raise SystemExit(1)

    LOG.info("Resource specification is valid.")


def setup_subparser(subparsers, parents):
    parser = subparsers.add_parser("validate", description=__doc__, parents=parents)
    parser.set_defaults(command=validate)
