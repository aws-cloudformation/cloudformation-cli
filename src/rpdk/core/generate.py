"""This sub command generates code from the project and resource schema.

Projects can be created via the 'init' sub command.
"""
import logging

from .project import Project

LOG = logging.getLogger(__name__)


def generate(args):
    project = Project()
    project.load()
    project.generate(args.endpoint_url, args.region, args.target_schemas)
    project.generate_docs()

    LOG.warning("Generated files for %s", project.type_name)


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("generate", description=__doc__, parents=parents)
    parser.set_defaults(command=generate)

    parser.add_argument("--endpoint-url", help="CloudFormation endpoint to use.")
    parser.add_argument("--region", help="AWS Region to submit the type.")
    parser.add_argument(
        "--target-schemas", help="Path to target schemas.", nargs="*", default=[]
    )
