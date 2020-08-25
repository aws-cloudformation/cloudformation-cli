"""This sub command generates IDE and build files for a given language.
"""
import logging
import re
from argparse import SUPPRESS
from functools import wraps

from colorama import Fore, Style

from .exceptions import WizardAbortError, WizardValidationError
from .plugin_registry import PLUGIN_CHOICES
from .project import Project

LOG = logging.getLogger(__name__)


TYPE_NAME_REGEX = r"^[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}$"


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
            print(Style.BRIGHT, Fore.RED, str(e), Style.RESET_ALL, sep="")


def validate_type_name(value):
    match = re.match(TYPE_NAME_REGEX, value)
    if match:
        return value
    LOG.debug("'%s' did not match '%s'", value, TYPE_NAME_REGEX)
    raise WizardValidationError(
        "Please enter a value matching '{}'".format(TYPE_NAME_REGEX)
    )


def validate_yes(value):
    return value.lower() in ("y", "yes")


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
    PLUGIN_CHOICES
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


def input_typename():
    type_name = input_with_validation(
        "What's the name of your resource type?",
        validate_type_name,
        "\n(Organization::Service::Resource)",
    )
    LOG.debug("Resource type identifier: %s", type_name)
    return type_name


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

    type_name = input_typename()
    if args.language:
        language = args.language
        LOG.warning("Language plugin '%s' selected non-interactively", language)
    else:
        language = input_language()

    project.init(type_name, language)
    project.generate()
    project.generate_docs()

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

    parser.add_argument(
        "--force", action="store_true", help="Force files to be overwritten."
    )
    # this is mainly for CI, so suppress it to keep it simple
    parser.add_argument("--language", help=SUPPRESS)
