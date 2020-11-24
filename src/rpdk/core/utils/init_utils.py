import logging

from colorama import Fore, Style

from rpdk.core.exceptions import WizardValidationError
from rpdk.core.project import ARTIFACT_TYPE_MODULE, ARTIFACT_TYPE_RESOURCE

LOG = logging.getLogger(__name__)

INPUT_TYPES_STRING = "resource(r) or a module(m)"
VALID_RESOURCES_REPRESENTATION = {"r", "resource", "resources"}
VALID_MODULES_REPRESENTATION = {"m", "module", "modules"}


# NOTE this function is also in init, for compatibility with language plugins
def init_artifact_type(args=None):
    if args and args.artifact_type:
        try:
            artifact_type = validate_artifact_type(args.artifact_type)
        except WizardValidationError as error:
            print_error(error)
            artifact_type = input_with_validation(
                "Do you want to develop a new {}?.".format(INPUT_TYPES_STRING),
                validate_artifact_type,
            )

    else:
        artifact_type = input_with_validation(
            "Do you want to develop a new {}?.".format(INPUT_TYPES_STRING),
            validate_artifact_type,
        )

    return artifact_type


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


def validate_artifact_type(value):
    if value.lower() in VALID_RESOURCES_REPRESENTATION:
        return ARTIFACT_TYPE_RESOURCE
    if value.lower() in VALID_MODULES_REPRESENTATION:
        return ARTIFACT_TYPE_MODULE
    raise WizardValidationError(
        "Please enter a value matching {}".format(INPUT_TYPES_STRING)
    )


def validate_yes(value):
    return value.lower() in ("y", "yes")
