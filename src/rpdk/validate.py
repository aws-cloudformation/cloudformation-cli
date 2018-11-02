"""This sub command validates a resource provider definition."""
import logging

from jsonschema.exceptions import ValidationError

from .argutils import TextFileType
from .data_loaders import load_resource_spec

LOG = logging.getLogger(__name__)


def validate(args):
    LOG.info("Validating your resource specification...")
    try:
        load_resource_spec(args.resource_spec_file)
    except ValidationError:
        LOG.error("Validation failed.")
    else:
        LOG.info("Validation succeeded.")


def setup_subparser(subparsers):
    parser = subparsers.add_parser("validate", description=__doc__)
    parser.set_defaults(command=validate)
    parser.add_argument(
        "resource_spec_file",
        type=TextFileType("r"),
        help="The resource specification to use for generating the code.",
    )
