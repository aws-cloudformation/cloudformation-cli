"""This sub command outputs the default project settings used for code
generation for a given language.
"""
import sys

from .argutils import TextFileType
from .plugin_registry import PLUGIN_REGISTRY, add_language_argument


def project_settings(args):
    plugin = PLUGIN_REGISTRY[args.language]
    with plugin.project_settings_defaults() as f:
        settings = f.read().decode("utf-8")
    args.output.write("# Project settings for {}\n".format(args.language))
    args.output.write(settings)


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser(
        "project-settings", description=__doc__, parents=parents
    )
    parser.set_defaults(command=project_settings)
    add_language_argument(parser)
    parser.add_argument(
        "--output",
        type=TextFileType("w"),
        default=sys.stdout,
        help="Where to output the project settings. (Default: stdout)",
    )
