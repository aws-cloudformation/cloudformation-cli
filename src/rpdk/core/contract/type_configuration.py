import json
import logging
import os

from rpdk.core.exceptions import InvalidProjectError

LOG = logging.getLogger(__name__)


class TypeConfiguration:
    TYPE_CONFIGURATION = None

    @staticmethod
    def get_type_configuration(typeconfigloc):
        if typeconfigloc:
            type_config_file_path = typeconfigloc
        else:
            type_config_file_path = "~/.cfn-cli/typeConfiguration.json"

        LOG.debug(
            "Loading type configuration setting file at %s",
            type_config_file_path,
        )
        if TypeConfiguration.TYPE_CONFIGURATION is None:
            try:
                with open(
                    os.path.expanduser(type_config_file_path), encoding="utf-8"
                ) as f:
                    TypeConfiguration.TYPE_CONFIGURATION = json.load(f)
            except json.JSONDecodeError as json_decode_error:
                LOG.debug(
                    "Type configuration file '%s' is invalid",
                    type_config_file_path,
                )
                raise InvalidProjectError(
                    "Type configuration file '%s' is invalid" % type_config_file_path
                ) from json_decode_error
            except FileNotFoundError:
                LOG.debug(
                    "Type configuration file '%s' not Found, do nothing",
                    type_config_file_path,
                )
        return TypeConfiguration.TYPE_CONFIGURATION

    @staticmethod
    def get_hook_configuration(typeconfigloc):
        type_configuration = TypeConfiguration.get_type_configuration(typeconfigloc)
        if type_configuration:
            try:
                return type_configuration.get("CloudFormationConfiguration", {})[
                    "HookConfiguration"
                ]["Properties"]
            except KeyError as e:
                LOG.warning("Hook configuration is invalid")
                raise InvalidProjectError("Hook configuration is invalid") from e
        return type_configuration
