"""This sub command generates IDE and build files for a given language.
"""
import logging
import os
from pathlib import Path

from .argutils import TextFileType
from .data_loaders import copy_resource, load_project_settings
from .plugin_registry import add_language_argument, get_plugin

LOG = logging.getLogger(__name__)


def init(args):
    plugin = get_plugin(args.language)

    LOG.info("Loading the project settings...")
    project_settings = load_project_settings(plugin, args.project_settings_file)
    project_settings["output_directory"] = args.output_directory
    project_settings["schemaFileName"] = "initech.tps.report.v1.json"

    LOG.info("Initializing project files...")
    output_path = Path(args.output_directory)
    output_path.mkdir(exist_ok=True)

    copy_resource(
        __name__,
        "data/examples/resource/initech.tps.report.v1.json",
        output_path / project_settings["schemaFileName"],
    )
    plugin.init(project_settings)


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("init", description=__doc__, parents=parents)
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
        type=TextFileType("r"),
        default=None,
        dest="project_settings_file",
        help=(
            "The project settings to use for initialization. "
            "These are language dependent. "
            "(Default: use default project settings)"
        ),
    )
