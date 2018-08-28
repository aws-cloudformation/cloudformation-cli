"""This sub command validates a resource provider definition."""
import argparse

from .data_loaders import load_resource_spec


def validate(args):
    print("Validating your resource schema...")
    if load_resource_spec(args.resource_spec_file):
        print("VALIDATION SUCCESS. You may proceed to code generation.")
    else:
        print("VALIDATION FAILED.")
    # todo: more validation beyond basic json, primarily json pointers.


def setup_subparser(subparsers):
    parser = subparsers.add_parser("validate", description=__doc__)
    parser.set_defaults(command=validate)
    parser.add_argument(
        "resource_spec_file",
        type=argparse.FileType("r"),
        help="The resource specification to use for generating the code.",
    )
