"""This sub command generates IDE and build files for a resource,
or schema files for a module.
"""
import argparse
import logging
import re
from functools import wraps

from colorama import Fore, Style

from .exceptions import WizardAbortError, WizardValidationError
from .module.init_module import init_module
from .plugin_registry import get_parsers, get_plugin_choices
from .project import ARTIFACT_TYPE_MODULE, Project
from .resource.init_resource import init_resource
from .utils.init_utils import init_artifact_type, validate_yes

LOG = logging.getLogger(__name__)


TYPE_NAME_REGEX = r"^[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}$"


def print_error(error):
    print(Style.BRIGHT, Fore.RED, str(error), Style.RESET_ALL, sep="")


def input_with_validation(prompt, validate, description=""):
    while True:
        print(
            Style.BRIGHT,
            Fore.WHITE,
            prompt,
            Style.RESET_ALL,
            description,
            Style.RESET_ALL,
            sep="",
        )
        print(Fore.YELLOW, ">> ", Style.RESET_ALL, sep="", end="")
        response = input()
        try:
            return validate(response)
        except WizardValidationError as e:
            print_error(e)


def validate_type_name(value):
    match = re.match(TYPE_NAME_REGEX, value)
    if match:
        return value
    LOG.debug("'%s' did not match '%s'", value, TYPE_NAME_REGEX)
    raise WizardValidationError(
        "Please enter a resource type name matching '{}'".format(TYPE_NAME_REGEX)
    )


class ValidatePluginChoice:
    def __init__(self, choices):
        self.choices = tuple(choices)
        self.max = len(self.choices)

        pretty = "\n".join(
            "[{}] {}".format(i, choice) for i, choice in enumerate(self.choices, 1)
        )
        self.message = (
            "Select a language for code generation:\n"
            + pretty
            + "\n(enter an integer): "
        )

    def __call__(self, value):
        try:
            choice = int(value)
        except ValueError:
            # pylint: disable=W0707
            raise WizardValidationError("Please enter an integer")
        choice -= 1
        if choice < 0 or choice >= self.max:
            raise WizardValidationError("Please select a choice")
        return self.choices[choice]


validate_plugin_choice = ValidatePluginChoice(  # pylint: disable=invalid-name
    get_plugin_choices()
)


def check_for_existing_project(project):
    try:
        project.load_settings()
    except FileNotFoundError:
        return  # good path

    if project.overwrite_enabled:
        LOG.warning("Overwriting settings file: %s", project.settings_path)
    else:
        LOG.debug(
            "Settings file for '%s' already exists: %s",
            project.type_name,
            project.settings_path,
        )
        project.overwrite_enabled = input_with_validation(
            "Found existing settings - overwrite (y/N)?",
            validate_yes,
            "\n" + project.type_name,
        )
        LOG.debug("Overwrite response: %s", project.overwrite_enabled)
        if not project.overwrite_enabled:
            raise WizardAbortError()


def input_language():
    # language/plugin
    if validate_plugin_choice.max < 1:
        LOG.critical("No language plugins found")
        raise WizardAbortError()

    if validate_plugin_choice.max == 1:
        language = validate_plugin_choice.choices[0]
        LOG.warning("One language plugin found, defaulting to %s", language)
    else:
        language = input_with_validation(
            validate_plugin_choice.message, validate_plugin_choice
        )
    LOG.debug("Language plugin: %s", language)
    return language


def init(args):
    project = Project(args.force)

    LOG.warning("Initializing new project")

    check_for_existing_project(project)

    artifact_type = init_artifact_type(args)

    if artifact_type == ARTIFACT_TYPE_MODULE:
        init_module(args, project)
    # artifact type can only be module or resource at this point
    else:
        init_resource(args, project)

    LOG.warning("Initialized a new project in %s", project.root.resolve())


def ignore_abort(function):
    @wraps(function)
    def wrapper(args):
        try:
            function(args)
        except (KeyboardInterrupt, WizardAbortError):
            print("\naborted")
            # pylint: disable=W0707
            raise SystemExit(1)

    return wrapper


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("init", description=__doc__, parents=parents)
    parser.set_defaults(command=ignore_abort(init))

    language_subparsers = parser.add_subparsers(dest="subparser_name")
    base_subparser = argparse.ArgumentParser(add_help=False)
    for language_setup_subparser in get_parsers().values():
        language_setup_subparser()(language_subparsers, [base_subparser])

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force files to be overwritten.",
    )

    parser.add_argument(
        "-t",
        "--type-name",
        help="Select the name of the type.",
    )

    parser.add_argument(
        "-a",
        "--artifact-type",
        help="Select the type of artifact (RESOURCE or MODULE)",
    )
