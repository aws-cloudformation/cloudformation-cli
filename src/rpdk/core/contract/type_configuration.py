import json
import logging
import os

from rpdk.core.exceptions import InvalidProjectError

LOG = logging.getLogger(__name__)

TYPE_CONFIGURATION_FILE_PATH = "~/.cfn-cli/typeConfiguration.json"


class TypeConfiguration:
    TYPE_CONFIGURATION = None

    @staticmethod
    def get_type_configuration():
        LOG.debug(
            "Loading type configuration setting file at '~/.cfn-cli/typeConfiguration.json'"
        )
        if TypeConfiguration.TYPE_CONFIGURATION is None:
            try:
                with open(
                    os.path.expanduser(TYPE_CONFIGURATION_FILE_PATH), encoding="utf-8"
                ) as f:
                    TypeConfiguration.TYPE_CONFIGURATION = json.load(f)
            except json.JSONDecodeError as json_decode_error:
                LOG.debug(
                    "Type configuration file '%s' is invalid",
                    TYPE_CONFIGURATION_FILE_PATH,
                )
                raise InvalidProjectError(
                    "Type configuration file '%s' is invalid"
                    % TYPE_CONFIGURATION_FILE_PATH
                ) from json_decode_error
            except FileNotFoundError:
                LOG.debug(
                    "Type configuration file '%s' not Found, do nothing",
                    TYPE_CONFIGURATION_FILE_PATH,
                )
        return TypeConfiguration.TYPE_CONFIGURATION

    @staticmethod
    def get_hook_configuration():
        type_configuration = TypeConfiguration.get_type_configuration()
        if type_configuration:
            try:
                return type_configuration.get("CloudFormationConfiguration", {})[
                    "HookConfiguration"
                ]["Properties"]
            except KeyError as e:
                LOG.warning("Hook configuration is invalid")
                raise InvalidProjectError("Hook configuration is invalid") from e
        return type_configuration
