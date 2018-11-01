"""This sub command generates IDE and build files for a given language.
"""
import argparse
import logging
import os
from pathlib import Path

from .data_loaders import copy_resource, load_project_settings
from .plugin_registry import PLUGIN_REGISTRY, add_language_argument

LOG = logging.getLogger(__name__)


def init(args):
    plugin = PLUGIN_REGISTRY[args.language]

    LOG.info("Loading the project settings...")
    project_settings = load_project_settings(plugin, args.project_settings_file)
    project_settings["output_directory"] = args.output_directory

    LOG.info("Initializing project files...")
    output_path = Path(args.output_directory)
    output_path.mkdir(exist_ok=True)

    copy_resource(
        __name__,
        "data/examples/resource/initech.tps.report.v1.json",
        output_path / "initech.tps.report.v1.json",
    )
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
