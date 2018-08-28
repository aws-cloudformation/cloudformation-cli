"""This sub command generates a basic resource provider code skeleton from a
resource provider definition and a given language.

Language-specific project settings can optionally be provided to further
customize the code generation.
"""
import argparse

import jinja2

from .data_loaders import load_project_settings, load_resource_spec
from .filters import FILTER_REGISTRY
from .generators.java import generate as generate_java

# registry decorators do not work well across files, so manual is simpler
LANGUAGE_GENERATOR_REGISTRY = {"java": generate_java}


def add_language_argument(parser):
    parser.add_argument(
        "--language",
        choices=list(LANGUAGE_GENERATOR_REGISTRY.keys()),
        default="java",
        help="The language for code generation. (Default: java)",
    )


def generate(args):
    print("Validating your resource schema and project settings...")
    resource_def = load_resource_spec(args.resource_def_file)
    project_settings = load_project_settings(args.language, args.project_settings_file)
    project_settings["output_directory"] = (
        args.output_directory if args.output_directory is not None else ""
    )
    print("VALIDATION SUCCESS. Proceeding to code generation...")

    generate_function = LANGUAGE_GENERATOR_REGISTRY[args.language]

    loader = jinja2.PackageLoader(__name__, "templates/" + args.language)
    env = jinja2.Environment(
        loader=loader, trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True
    )
    for filter_name, filter_func in FILTER_REGISTRY.items():
        env.filters[filter_name] = filter_func

    env.trim_blocks = True
    env.lstrip_blocks = True
    env.keep_trailing_newline = True

    generate_function(env, resource_def, project_settings)
    print("CODE GENERATION SUCCESS.")


def setup_subparser(subparsers):
    # see docstring of this file
    parser = subparsers.add_parser("generate", description=__doc__)
    parser.set_defaults(command=generate)
    parser.add_argument(
        "resource_def_file",
        type=argparse.FileType("r"),
        help="The resource provider definition to use for code generation.",
    )
    add_language_argument(parser)
    parser.add_argument(
        "--output-directory",
        dest="output_directory",
        help="Output directory for sample schema.",
    )
    # we should always be able to provide some kind of default project setting,
    # so the user doesn't need to look these up before trying out codegen.
    # this reduces on-boarding friction, as the resource definition is already quite
    # a lot of effort. maybe we should have another command to write these
    # defaults to a file?
    parser.add_argument(
        "--project-settings",
        type=argparse.FileType("r"),
        default=None,
        dest="project_settings_file",
        help=(
            "The project settings to use for generation. "
            "These are language dependent. "
            "(Default: use default project settings)"
        ),
    )
