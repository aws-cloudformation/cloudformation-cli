from colorama import Fore, Style
from rpdk.core.exceptions import WizardValidationError


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


def validate_yes(value):
    return value.lower() in ("y", "yes")
