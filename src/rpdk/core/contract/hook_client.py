# pylint: disable=import-outside-toplevel
# pylint: disable=R0904
# have to skip B404, import_subprocess is required for executing typescript
# have to skip B60*, to allow typescript code to be executed using subprocess
import json
import logging
import re
import time
from uuid import uuid4

import docker
from botocore import UNSIGNED
from botocore.config import Config
from jinja2 import Environment, PackageLoader, select_autoescape

from rpdk.core.boto_helpers import (
    LOWER_CAMEL_CRED_KEYS,
    create_sdk_session,
    get_account,
    get_temporary_credentials,
)
from rpdk.core.contract.interface import (
    HandlerErrorCode,
    HookInvocationPoint,
    HookStatus,
)
from rpdk.core.contract.resource_client import override_properties, prune_properties
from rpdk.core.contract.type_configuration import TypeConfiguration
from rpdk.core.exceptions import InvalidProjectError
from rpdk.core.utils.handler_utils import generate_handler_name

from ..jsonutils.pointer import fragment_decode

LOG = logging.getLogger(__name__)


def override_target_properties(document, overrides):
    overridden = dict(document)
    for key, value in document.items():
        overridden[key] = override_properties(value, overrides.get(key, {}))
    return overridden


class HookClient:  # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        function_name,
        endpoint,
        region,
        schema,
        overrides,
        inputs=None,
        role_arn=None,
        timeout_in_seconds="60",
        type_name=None,
        log_group_name=None,
        log_role_arn=None,
        docker_image=None,
        executable_entrypoint=None,
        target_info=None,
    ):  # pylint: disable=too-many-arguments
        self._schema = schema
        self._session = create_sdk_session(region)
        self._role_arn = role_arn
        self._type_name = type_name
        self._log_group_name = log_group_name
        self._log_role_arn = log_role_arn
        self.region = region
        self.account = get_account(
            self._session,
            get_temporary_credentials(self._session, LOWER_CAMEL_CRED_KEYS, role_arn),
        )
        self._function_name = function_name
        if endpoint.startswith("http://"):
            self._client = self._session.client(
                "lambda",
                endpoint_url=endpoint,
                use_ssl=False,
                verify=False,
                config=Config(
                    signature_version=UNSIGNED,
                    # needs to be long if docker is running on a slow machine
                    read_timeout=5 * 60,
                    retries={"max_attempts": 0},
                    region_name=self._session.region_name,
                ),
            )
        else:
            self._client = self._session.client("lambda", endpoint_url=endpoint)

        self._schema = None
        self._configuration_schema = None
        self._overrides = overrides
        self._update_schema(schema)
        self._inputs = inputs
        self._timeout_in_seconds = int(timeout_in_seconds)
        self._docker_image = docker_image
        self._docker_client = docker.from_env() if self._docker_image else None
        self._executable_entrypoint = executable_entrypoint
        self._target_info = self._setup_target_info(target_info)

    @staticmethod
    def _properties_to_paths(schema, key):
        return {fragment_decode(prop, prefix="") for prop in schema.get(key, [])}

    @staticmethod
    def _setup_target_info(hook_target_info):
        if not hook_target_info:
            return hook_target_info

        target_info = dict(hook_target_info)
        for target, info in target_info.items():
            LOG.debug("Setting up target info for '%s'", target)

            # make a copy so the original schema is never modified
            target_schema = json.loads(json.dumps(info["Schema"]))

            info["readOnlyProperties"] = HookClient._properties_to_paths(
                target_schema, "readOnlyProperties"
            )
            info["createOnlyProperties"] = HookClient._properties_to_paths(
                target_schema, "createOnlyProperties"
            )

        return target_info

    def _update_schema(self, schema):
        # TODO: resolve $ref
        self.env = Environment(
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            loader=PackageLoader(__name__, "templates/"),
            autoescape=select_autoescape(["html", "htm", "xml", "md"]),
        )
        self._schema = schema
        self._configuration_schema = schema.get("typeConfiguration")

    def get_hook_type_name(self):
        return self._type_name if self._type_name else self._schema["typeName"]

    def get_handler_targets(self, invocation_point):
        try:
            handlers = self._schema["handlers"]
            handler = handlers[generate_handler_name(invocation_point)]
            return handler["targetNames"]
        except KeyError:
            return set()

    @staticmethod
    def assert_in_progress(status, response, target=""):
        assert (
            status == HookStatus.IN_PROGRESS
        ), f"status should be IN_PROGRESS ({target})"
        assert (
            response.get("errorCode", 0) == 0
        ), f"IN_PROGRESS events should have no error code set ({target})"
        assert (
            response.get("result") is None
        ), f"IN_PROGRESS events should have no result ({target})"

        return response.get("callbackDelaySeconds", 0)

    @staticmethod
    def assert_success(status, response, target=""):
        assert status == HookStatus.SUCCESS, f"status should be SUCCESS ({target})"
        assert (
            response.get("errorCode", 0) == 0
        ), f"SUCCESS events should have no error code set ({target})"
        assert (
            response.get("callbackDelaySeconds", 0) == 0
        ), f"SUCCESS events should have no callback delay ({target})"

    @staticmethod
    def assert_failed(status, response, target=""):
        assert status == HookStatus.FAILED, f"status should be FAILED ({target})"
        assert (
            "errorCode" in response
        ), f"FAILED events must have an error code set ({target})"
        # raises a KeyError if the error code is invalid
        error_code = HandlerErrorCode[response["errorCode"]]
        assert (
            response.get("callbackDelaySeconds", 0) == 0
        ), f"FAILED events should have no callback delay ({target})"
        assert (
            response.get("message") is not None
        ), f"FAILED events should have a message ({target})"

        return error_code

    @staticmethod
    # pylint: disable=R0913
    def make_request(
        target_name,
        hook_type_name,
        account,
        invocation_point,
        creds,
        log_group_name,
        log_creds,
        token,
        target_model,
        hook_type_version="00000001",
        target_type="RESOURCE",
        callback_context=None,
        type_configuration=None,
        **kwargs,
    ):
        request_body = {
            "requestData": {
                "callerCredentials": creds
                if isinstance(creds, str)
                else json.dumps(creds),
                "targetName": target_name,
                "targetType": target_type,
                "targetLogicalId": token,
                "targetModel": target_model,
            },
            "requestContext": {"callbackContext": callback_context},
            "hookTypeName": hook_type_name,
            "hookTypeVersion": hook_type_version,
            "clientRequestToken": token,
            "stackId": token,
            "awsAccountId": account,
            "actionInvocationPoint": invocation_point,
            "hookModel": type_configuration,
            **kwargs,
        }
        if log_group_name and log_creds:
            request_body["requestData"]["providerLogGroupName"] = log_group_name
            request_body["requestData"]["providerCredentials"] = (
                log_creds if isinstance(log_creds, str) else json.dumps(log_creds)
            )
        return request_body

    def _generate_target_example(self, target):
        LOG.debug("Generating example for target '%s'", target)
        if not self._target_info or not self._target_info.get(target):
            return {}

        info = self._target_info.get(target)
        if not info.get("SchemaStrategy"):
            # imported here to avoid hypothesis being loaded before pytest is loaded
            from .resource_generator import ResourceGenerator

            # make a copy so the original schema is never modified
            target_schema = json.loads(json.dumps(info["Schema"]))

            prune_properties(target_schema, info["readOnlyProperties"])

            info["SchemaStrategy"] = ResourceGenerator(
                target_schema
            ).generate_schema_strategy(target_schema)

        return info.get("SchemaStrategy").example()

    def _generate_target_update_example(self, target, model):
        LOG.debug("Generating update example for target '%s'", target)
        if not self._target_info or not self._target_info.get(target):
            return {}

        info = self._target_info.get(target)
        if not info.get("UpdateSchemaStrategy"):
            # imported here to avoid hypothesis being loaded before pytest is loaded
            from .resource_generator import ResourceGenerator

            # make a copy so the original schema is never modified
            target_schema = json.loads(json.dumps(info["Schema"]))

            prune_properties(target_schema, info["readOnlyProperties"])
            prune_properties(target_schema, info["createOnlyProperties"])

            info["UpdateSchemaStrategy"] = ResourceGenerator(
                target_schema
            ).generate_schema_strategy(target_schema)

        example = info.get("UpdateSchemaStrategy").example()
        return {**model, **example}

    def _generate_target_model(self, target, invocation_point):
        if self._inputs:
            if "INVALID" in invocation_point:
                try:
                    return self._inputs[invocation_point][target]
                except KeyError:
                    return self._inputs["INVALID"][target]
            return self._inputs[invocation_point][target]

        target_example = self._generate_target_example(target)
        if "UPDATE_PRE_PROVISION" in invocation_point:
            target_model = {
                "resourceProperties": self._generate_target_update_example(
                    target, target_example
                ),
                "previousResourceProperties": target_example,
            }
        else:
            target_model = {"resourceProperties": target_example}

        if "INVALID" in invocation_point:
            overrides = self._overrides.get(
                invocation_point, self._overrides.get("INVALID", {})
            ).get(target, {})
        elif "UPDATE_PRE_PROVISION" in invocation_point:
            overrides = self._overrides.get(
                "UPDATE_PRE_PROVISION", self._overrides.get("CREATE_PRE_PROVISION", {})
            ).get(target, {})
        else:
            overrides = self._overrides.get(invocation_point, {}).get(target, {})

        return override_target_properties(target_model, overrides)

    def generate_request(self, target, invocation_point):
        target_model = self._generate_target_model(target, invocation_point.name)
        return self._make_payload(invocation_point, target, target_model)

    def generate_invalid_request(self, target, invocation_point):
        target_model = self._generate_target_model(
            target, f"INVALID_{invocation_point.name}"
        )
        return self._make_payload(invocation_point, target, target_model)

    def generate_request_example(self, target, invocation_point):
        request = self.generate_request(target, invocation_point)
        target_model = request["requestData"]["targetModel"]

        return invocation_point, target, target_model

    def generate_invalid_request_example(self, target, invocation_point):
        request = self.generate_invalid_request(target, invocation_point)
        target_model = request["requestData"]["targetModel"]

        return invocation_point, target, target_model

    def generate_request_examples(self, invocation_point):
        return [
            self.generate_request_example(target, invocation_point)
            for target in self.get_handler_targets(invocation_point)
        ]

    def generate_invalid_request_examples(self, invocation_point):
        return [
            self.generate_invalid_request_example(target, invocation_point)
            for target in self.get_handler_targets(invocation_point)
        ]

    def generate_all_request_examples(self):
        examples = {}
        for invoke_point in HookInvocationPoint:
            examples[invoke_point] = self.generate_request_examples(invoke_point)
        return examples

    @staticmethod
    def generate_token():
        return str(uuid4())

    @staticmethod
    def is_update_invocation_point(invocation_point):
        return invocation_point in (HookInvocationPoint.UPDATE_PRE_PROVISION,)

    def assert_time(self, start_time, end_time, action):
        timeout_in_seconds = self._timeout_in_seconds
        assert end_time - start_time <= timeout_in_seconds, (
            "Handler %r timed out." % action
        )

    def _make_payload(
        self,
        invocation_point,
        target,
        target_model,
        type_configuration=None,
        **kwargs,
    ):
        return self.make_request(
            target,
            self.get_hook_type_name(),
            self.account,
            invocation_point,
            get_temporary_credentials(
                self._session, LOWER_CAMEL_CRED_KEYS, self._role_arn
            ),
            self._log_group_name,
            get_temporary_credentials(
                self._session, LOWER_CAMEL_CRED_KEYS, self._log_role_arn
            ),
            self.generate_token(),
            target_model,
            type_configuration=type_configuration,
            **kwargs,
        )

    def _call(self, payload):
        payload_to_log = {
            "hookTypeName": payload["hookTypeName"],
            "actionInvocationPoint": payload["actionInvocationPoint"],
            "requestData": {
                "targetName": payload["requestData"]["targetName"],
                "targetLogicalId": payload["requestData"]["targetLogicalId"],
                "targetModel": payload["requestData"]["targetModel"],
            },
            "awsAccountId": payload["awsAccountId"],
            "clientRequestToken": payload["clientRequestToken"],
        }

        LOG.debug(
            "Sending request\n%s",
            json.dumps(payload_to_log, ensure_ascii=False, indent=2),
        )
        payload = json.dumps(payload, ensure_ascii=False, indent=2)
        if self._docker_image:
            if not self._executable_entrypoint:
                raise InvalidProjectError(
                    "executableEntrypoint not set in .rpdk-config. "
                    "Have you run cfn generate?"
                )
            result = (
                self._docker_client.containers.run(
                    self._docker_image,
                    self._executable_entrypoint + " '" + payload + "'",
                    environment={"AWS_REGION": self.region},
                )
                .decode()
                .strip()
            )
            LOG.debug("=== Handler execution logs ===")
            LOG.debug(result)
            # pylint: disable=W1401
            regex = "__CFN_HOOK_START_RESPONSE__([\s\S]*)__CFN_HOOK_END_RESPONSE__"  # noqa: W605,B950 # pylint: disable=C0301
            payload = json.loads(re.search(regex, result).group(1))
        else:
            result = self._client.invoke(
                FunctionName=self._function_name, Payload=payload.encode("utf-8")
            )

            try:
                payload = json.load(result["Payload"])
            except json.decoder.JSONDecodeError as json_error:
                LOG.debug("Received invalid response\n%s", result["Payload"])
                raise ValueError(
                    "Handler Output is not a valid JSON document"
                ) from json_error

        LOG.debug("Received response\n%s", json.dumps(payload, indent=2))
        return payload

    # pylint: disable=R0913
    def call_and_assert(
        self,
        invocation_point,
        assert_status,
        target,
        target_model,
        **kwargs,
    ):
        if assert_status not in [HookStatus.SUCCESS, HookStatus.FAILED]:
            raise ValueError("Assert status {} not supported.".format(assert_status))

        status, response = self.call(invocation_point, target, target_model, **kwargs)
        if assert_status == HookStatus.SUCCESS:
            self.assert_success(status, response, target)
            error_code = None
        else:
            error_code = self.assert_failed(status, response, target)
        return status, response, error_code

    def call(
        self,
        invocation_point,
        target,
        target_model,
        **kwargs,
    ):
        request = self._make_payload(
            invocation_point,
            target,
            target_model,
            TypeConfiguration.get_hook_configuration(),
            **kwargs,
        )
        start_time = time.time()
        response = self._call(request)
        self.assert_time(start_time, time.time(), invocation_point)

        # this throws a KeyError if status isn't present, or if it isn't a valid status
        status = HookStatus[response["hookStatus"]]

        while status == HookStatus.IN_PROGRESS:
            callback_delay_seconds = self.assert_in_progress(status, response, target)
            time.sleep(callback_delay_seconds)

            request["requestContext"]["callbackContext"] = response.get(
                "callbackContext"
            )

            response = self._call(request)
            status = HookStatus[response["hookStatus"]]

        return status, response
