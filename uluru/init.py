"""This sub command generates IDE and build files for a given language.
"""
import argparse
import logging
import os

from .data_loaders import load_project_settings
from .plugin_registry import PLUGIN_REGISTRY, add_language_argument

LOG = logging.getLogger(__name__)


def init(args):
    plugin = PLUGIN_REGISTRY[args.language]

    LOG.info("Loading the project settings...")
    project_settings = load_project_settings(plugin, args.project_settings_file)
    project_settings["output_directory"] = args.output_directory

    LOG.info("Initializing project files...")
    plugin.init(project_settings)


def setup_subparser(subparsers):
    # see docstring of this file
    parser = subparsers.add_parser("init", description=__doc__)
    parser.set_defaults(command=init)
    parser.add_argument(
        "--output-directory",
        dest="output_directory",
        default=os.getcwd(),
        help="Output directory for initialization. (Default: current directory)",
    )
    add_language_argument(parser)
    parser.add_argument(
        "--project-settings",
        type=argparse.FileType("r"),
        default=None,
        dest="project_settings_file",
        help=(
            "The project settings to use for initialization. "
            "These are language dependent. "
            "(Default: use default project settings)"
        ),
    )
