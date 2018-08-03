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
LANGUAGE_GENERATOR_REGISTRY = {
    'java': generate_java,
}


def add_language_argument(parser):
    parser.add_argument(
        '--language',
        choices=list(LANGUAGE_GENERATOR_REGISTRY.keys()),
        default='java',
        help='The language for code generation. (Default: java)')


def generate(args):
    resource_spec = load_resource_spec(args.resource_def_file)
    project_settings = load_project_settings(
        args.language, args.project_settings_file)

    generate_function = LANGUAGE_GENERATOR_REGISTRY[args.language]

    loader = jinja2.PackageLoader(__name__, 'templates/' + args.language)
    env = jinja2.Environment(loader=loader)
    for filter_name, filter_func in FILTER_REGISTRY.items():
        env.filters[filter_name] = filter_func
    generate_function(env, resource_spec, project_settings)


def setup_subparser(subparsers):
    # see docstring of this file
    parser = subparsers.add_parser('generate', description=__doc__)
    parser.set_defaults(command=generate)
    parser.add_argument(
        'resource_def_file',
        type=argparse.FileType('r'),
        help='The resource provider definition to use for code generation.')
    add_language_argument(parser)
    parser.add_argument(
        '--project-settings',
        type=argparse.FileType('r'),
        default=None,
        dest='project_settings_file',
        help=(
            'The project settings to use for generation. '
            'These are language dependent. '
            '(Default: use default project settings)'
        ))
