import logging
import re

from rpdk.core.exceptions import WizardValidationError
from rpdk.core.fragment.generator import TemplateFragment
from rpdk.core.utils.init_utils import input_with_validation, print_error

LOG = logging.getLogger(__name__)

# this regex has to be kept in sync with the one in the meta-schema.
MODULE_TYPE_NAME_REGEX = (
    r"^[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}::MODULE$"
)


def init_module(args, project):
    if args.type_name:
        try:
            type_name = validate_type_name(args.type_name)
        except WizardValidationError as error:
            print_error(error)
            type_name = input_typename()
    else:
        type_name = input_typename()

    project.init_module(type_name)
    template_fragment = TemplateFragment(type_name)
    template_fragment.generate_sample_fragment()


def input_typename():
    type_name = input_with_validation(
        "What's the name of your module type?",
        validate_type_name,
        "\n(<Organization>::<Service>::<Name>::MODULE)",
    )
    LOG.debug("Resource type identifier: %s", type_name)
    return type_name


def validate_type_name(value):
    match = re.match(MODULE_TYPE_NAME_REGEX, value)
    if match:
        return value
    LOG.debug("'%s' did not match '%s'", value, MODULE_TYPE_NAME_REGEX)
    raise WizardValidationError(
        "Please enter a value matching '{}'".format(MODULE_TYPE_NAME_REGEX)
    )
