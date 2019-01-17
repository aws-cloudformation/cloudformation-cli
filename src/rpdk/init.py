"""This sub command generates IDE and build files for a given language.
"""
import logging
import re
from functools import wraps

from .plugin_registry import PLUGIN_CHOICES
from .project import Project

LOG = logging.getLogger(__name__)


TYPE_NAME_REGEX = r"^[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}$"


class AbortError(Exception):
    pass


class ValidationError(Exception):
    pass


def input_with_validation(prompt, validate):
    while True:
        response = input(prompt)
        try:
            return validate(response)
        except ValidationError as e:
            print(str(e))


def validate_type_name(value):
    match = re.match(TYPE_NAME_REGEX, value)
    if match:
        return value
    LOG.debug("'%s' did not match '%s'", value, TYPE_NAME_REGEX)
    raise ValidationError("Please enter a value matching '{}'".format(TYPE_NAME_REGEX))


def validate_yes(value):
    return value.lower() in ("y", "yes")


class ValidatePluginChoice:
    def __init__(self, choices):
        self.choices = tuple(choices)
        self.max = len(self.choices)

        pretty = "\n".join(
            "[{}] {}".format(i, choice) for i, choice in enumerate(self.choices, 1)
        )
        self.message = "Select a language for code generation:\n" + pretty

    def __call__(self, value):
        try:
            choice = int(value)
        except ValueError:
            raise ValidationError("Please enter an integer")
        choice -= 1
        if choice < 0 or choice >= self.max:
            raise ValidationError("Please select a choice")
        return self.choices[choice]


validate_plugin_choice = ValidatePluginChoice(  # pylint: disable=invalid-name
    PLUGIN_CHOICES
)


def check_for_existing_project(project):
    try:
        project.load_settings()
    except FileNotFoundError:
        return  # good path

    if project.overwrite:
        LOG.warning("Overwriting settings file: %s", project.settings_path)
    else:
        LOG.debug(
            "Settings file for '%s' already exists: %s",
            project.type_name,
            project.settings_path,
        )
        project.overwrite = input_with_validation(
            "Overwrite existing settings (y/N)? ", validate_yes
        )
        LOG.debug("Overwrite response: %s", project.overwrite)
        if not project.overwrite:
            raise AbortError()


def input_typename():
    type_name = input_with_validation(
        "Enter resource type identifier (Organization::Service::Resource): ",
        validate_type_name,
    )
    LOG.debug("Resource type identifier: %s", type_name)
    return type_name


def input_language():
    # language/plugin
    if validate_plugin_choice.max < 1:
        LOG.critical("No language plugins found")
        raise AbortError()

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
    language = input_language()

    project.init(type_name, language)
    project.generate()


def ignore_abort(function):
    @wraps(function)
    def wrapper(args):
        try:
            function(args)
        except (KeyboardInterrupt, AbortError):
            print("\naborted")
            raise SystemExit(1)

    return wrapper


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("init", description=__doc__, parents=parents)
    parser.set_defaults(command=ignore_abort(init))

    parser.add_argument(
        "--force", action="store_true", help="Force files to be overwritten."
    )
