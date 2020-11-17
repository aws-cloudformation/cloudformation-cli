# pylint: disable=import-outside-toplevel
# pylint: disable=R0904
import json
import logging
import re
import time
from time import sleep
from uuid import uuid4

import docker
from botocore import UNSIGNED
from botocore.config import Config

from rpdk.core.contract.interface import Action, HandlerErrorCode, OperationStatus
from rpdk.core.exceptions import InvalidProjectError

from ..boto_helpers import (
    LOWER_CAMEL_CRED_KEYS,
    create_sdk_session,
    get_account,
    get_temporary_credentials,
)
from ..jsonutils.pointer import fragment_decode, fragment_list
from ..jsonutils.utils import traverse

LOG = logging.getLogger(__name__)


def prune_properties(document, paths):
    """Prune given properties from a document.

    This assumes properties will always have an object (dict) as a parent.
    The function modifies the document in-place, but also returns the document
    for convenience. (The return value may be ignored.)
    """
    for path in paths:
        try:
            _prop, resolved_path, parent = traverse(document, path)
        except LookupError:
            pass  # not found means nothing to delete
        else:
            key = resolved_path[-1]
            del parent[key]
    return document


def prune_properties_if_not_exist_in_path(output_model, input_model, paths):
    """Prune given properties from a model.

    This assumes properties will always have an object (dict) as a parent.
    The function returns the model after pruning the path which exists
    in the paths tuple but not in the input_model
    """
    output_document = {"properties": output_model.copy()}
    input_document = {"properties": input_model.copy()}
    for path in paths:
        try:
            if not path_exists(input_document, path):
                _prop, resolved_path, parent = traverse(output_document, path)
                key = resolved_path[-1]
                del parent[key]
        except LookupError:
            pass
    return output_document["properties"]


def path_exists(document, path):
    try:
        _prop, _resolved_path, _parent = traverse(document, path)
    except LookupError:
        return False
    else:
        return True


def prune_properties_from_model(model, paths):
    """Prune given properties from a resource model.

    This assumes the dict passed in is a resources model i.e. solely the properties.
    This also assumes the paths to remove are prefixed with "/properties",
    as many of the paths are defined in the schema
    The function modifies the document in-place, but also returns the document
    for convenience. (The return value may be ignored.)
    """
    return prune_properties({"properties": model}, paths)["properties"]


def override_properties(document, overrides):
    """Override given properties from a document."""
    for path, obj in overrides.items():
        try:
            _prop, resolved_path, parent = traverse(document, path)
        except LookupError:
            LOG.debug(
                "Override failed.\nPath %s\nObject %s\nDocument %s", path, obj, document
            )
            LOG.warning("Override with path %s not found, skipping", path)
        else:
            key = resolved_path[-1]
            parent[key] = obj
    return document


class ResourceClient:  # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        function_name,
        endpoint,
        region,
        schema,
        overrides,
        inputs=None,
        role_arn=None,
        timeout_in_seconds="30",
        docker_image=None,
        executable_entrypoint=None,
    ):  # pylint: disable=too-many-arguments
        self._schema = schema
        self._session = create_sdk_session(region)
        self._role_arn = role_arn
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
        self._strategy = None
        self._update_strategy = None
        self._invalid_strategy = None
        self._overrides = overrides
        self._update_schema(schema)
        self._inputs = inputs
        self._timeout_in_seconds = int(timeout_in_seconds)
        self._docker_image = docker_image
        self._docker_client = docker.from_env() if self._docker_image else None
        self._executable_entrypoint = executable_entrypoint

    def _properties_to_paths(self, key):
        return {fragment_decode(prop, prefix="") for prop in self._schema.get(key, [])}

    def _update_schema(self, schema):
        # TODO: resolve $ref
        self._schema = schema
        self._strategy = None
        self._update_strategy = None
        self._invalid_strategy = None

        self.primary_identifier_paths = self._properties_to_paths("primaryIdentifier")
        self.read_only_paths = self._properties_to_paths("readOnlyProperties")
        self.write_only_paths = self._properties_to_paths("writeOnlyProperties")
        self.create_only_paths = self._properties_to_paths("createOnlyProperties")
        self.properties_without_insertion_order = self.get_metadata()

        additional_identifiers = self._schema.get("additionalIdentifiers", [])
        self._additional_identifiers_paths = [
            {fragment_decode(prop, prefix="") for prop in identifier}
            for identifier in additional_identifiers
        ]

    def has_only_writable_identifiers(self):
        return all(
            path in self.create_only_paths for path in self.primary_identifier_paths
        )

    def assert_write_only_property_does_not_exist(self, resource_model):
        if self.write_only_paths:
            assert not any(
                self.key_error_safe_traverse(resource_model, write_only_property)
                for write_only_property in self.write_only_paths
            ), "The model MUST NOT return properties defined as \
                writeOnlyProperties in the resource schema"

    def get_metadata(self):
        try:
            properties = self._schema["properties"]
        except KeyError:
            return set()
        else:
            return {
                prop
                for prop in properties.keys()
                if "insertionOrder" in properties[prop]
                and properties[prop]["insertionOrder"] == "false"
            }

    @property
    def strategy(self):
        # an empty strategy (i.e. false-y) is valid
        if self._strategy is not None:
            return self._strategy

        # imported here to avoid hypothesis being loaded before pytest is loaded
        from .resource_generator import ResourceGenerator

        # make a copy so the original schema is never modified
        schema = json.loads(json.dumps(self._schema))

        prune_properties(schema, self.read_only_paths)

        self._strategy = ResourceGenerator(schema).generate_schema_strategy(schema)
        return self._strategy

    @property
    def invalid_strategy(self):
        # an empty strategy (i.e. false-y) is valid
        if self._invalid_strategy is not None:
            return self._invalid_strategy

        # imported here to avoid hypothesis being loaded before pytest is loaded
        from .resource_generator import ResourceGenerator

        # make a copy so the original schema is never modified
        schema = json.loads(json.dumps(self._schema))

        self._invalid_strategy = ResourceGenerator(schema).generate_schema_strategy(
            schema
        )
        return self._invalid_strategy

    @property
    def update_strategy(self):
        # an empty strategy (i.e. false-y) is valid
        if self._update_strategy is not None:
            return self._update_strategy

        # imported here to avoid hypothesis being loaded before pytest is loaded
        from .resource_generator import ResourceGenerator

        # make a copy so the original schema is never modified
        schema = json.loads(json.dumps(self._schema))

        prune_properties(schema, self.read_only_paths)
        prune_properties(schema, self.create_only_paths)

        self._update_strategy = ResourceGenerator(schema).generate_schema_strategy(
            schema
        )
        return self._update_strategy

    def generate_create_example(self):
        if self._inputs:
            return self._inputs["CREATE"]
        example = self.strategy.example()
        return override_properties(example, self._overrides.get("CREATE", {}))

    def generate_invalid_create_example(self):
        if self._inputs:
            return self._inputs["INVALID"]
        example = self.invalid_strategy.example()
        return override_properties(example, self._overrides.get("CREATE", {}))

    def get_unique_keys_for_model(self, create_model):
        return {
            k: v
            for k, v in create_model.items()
            if self.is_property_in_path(k, self.primary_identifier_paths)
            or self.is_property_in_path(k, self._additional_identifiers_paths)
        }

    @staticmethod
    def is_property_in_path(key, paths):
        for path in paths:
            prop = fragment_list(path, "properties")[0]
            if prop == key:
                return True
        return False

    def validate_update_example_keys(self, unique_identifiers, update_example):
        for primary_identifier in self.primary_identifier_paths:
            if primary_identifier in self.create_only_paths:
                primary_key = fragment_list(primary_identifier, "properties")[0]
                assert update_example[primary_key] == unique_identifiers[primary_key], (
                    "Any createOnlyProperties specified in update handler input "
                    "MUST NOT be different from their previous state"
                )

    def generate_update_example(self, create_model):
        if self._inputs:
            unique_identifiers = self.get_unique_keys_for_model(create_model)
            update_example = self._inputs["UPDATE"]
            if self.create_only_paths:
                self.validate_update_example_keys(unique_identifiers, update_example)
            update_example.update(unique_identifiers)
            return update_example
        overrides = self._overrides.get("UPDATE", self._overrides.get("CREATE", {}))
        example = override_properties(self.update_strategy.example(), overrides)
        return {**create_model, **example}

    def generate_invalid_update_example(self, create_model):
        if self._inputs:
            return self._inputs["INVALID"]
        overrides = self._overrides.get("UPDATE", self._overrides.get("CREATE", {}))
        example = override_properties(self.invalid_strategy.example(), overrides)
        return {**create_model, **example}

    @staticmethod
    def key_error_safe_traverse(resource_model, write_only_property):
        try:
            return traverse(
                resource_model, fragment_list(write_only_property, "properties")
            )[0]
        except KeyError:
            return None

    @staticmethod
    def assert_in_progress(status, response):
        assert status == OperationStatus.IN_PROGRESS, "status should be IN_PROGRESS"
        assert (
            response.get("errorCode", 0) == 0
        ), "IN_PROGRESS events should have no error code set"
        assert (
            response.get("resourceModels") is None
        ), "IN_PROGRESS events should not include any resource models"

        return response.get("callbackDelaySeconds", 0)

    @staticmethod
    def assert_success(status, response):
        assert status == OperationStatus.SUCCESS, "status should be SUCCESS"
        assert (
            response.get("errorCode", 0) == 0
        ), "SUCCESS events should have no error code set"
        assert (
            response.get("callbackDelaySeconds", 0) == 0
        ), "SUCCESS events should have no callback delay"

    @staticmethod
    def assert_failed(status, response):
        assert status == OperationStatus.FAILED, "status should be FAILED"
        assert "errorCode" in response, "FAILED events must have an error code set"
        # raises a KeyError if the error code is invalid
        error_code = HandlerErrorCode[response["errorCode"]]
        assert (
            response.get("callbackDelaySeconds", 0) == 0
        ), "FAILED events should have no callback delay"
        assert (
            response.get("resourceModels") is None
        ), "FAILED events should not include any resource models"

        return error_code

    @staticmethod
    # pylint: disable=R0913
    def make_request(
        desired_resource_state,
        previous_resource_state,
        region,
        account,
        action,
        creds,
        token,
        callback_context=None,
        **kwargs
    ):
        return {
            "requestData": {
                "callerCredentials": creds,
                "resourceProperties": desired_resource_state,
                "previousResourceProperties": previous_resource_state,
                "logicalResourceId": token,
            },
            "region": region,
            "awsAccountId": account,
            "action": action,
            "callbackContext": callback_context,
            "bearerToken": token,
            **kwargs,
        }

    @staticmethod
    def generate_token():
        return str(uuid4())

    def assert_time(self, start_time, end_time, action):
        timeout_in_seconds = (
            self._timeout_in_seconds
            if action in (Action.READ, Action.LIST)
            else self._timeout_in_seconds * 2
        )
        assert end_time - start_time <= timeout_in_seconds, (
            "Handler %r timed out." % action
        )

    @staticmethod
    def assert_primary_identifier(primary_identifier_paths, resource_model):
        try:
            assert all(
                traverse(
                    resource_model, fragment_list(primary_identifier, "properties")
                )[0]
                for primary_identifier in primary_identifier_paths
            ), "Every returned model MUST include the primaryIdentifier"
        except KeyError as e:
            raise AssertionError(
                "Every returned model MUST include the primaryIdentifier"
            ) from e

    @staticmethod
    def is_primary_identifier_equal(
        primary_identifier_path, created_model, updated_model
    ):
        try:
            return all(
                traverse(
                    created_model, fragment_list(primary_identifier, "properties")
                )[0]
                == traverse(
                    updated_model, fragment_list(primary_identifier, "properties")
                )[0]
                for primary_identifier in primary_identifier_path
            )
        except KeyError as e:
            raise AssertionError(
                "The primaryIdentifier returned in every progress event must\
                     match the primaryIdentifier passed into the request"
            ) from e

    def _make_payload(self, action, current_model, previous_model=None, **kwargs):
        return self.make_request(
            current_model,
            previous_model,
            self.region,
            self.account,
            action,
            get_temporary_credentials(
                self._session, LOWER_CAMEL_CRED_KEYS, self._role_arn
            ),
            self.generate_token(),
            **kwargs
        )

    def _call(self, payload):
        request_without_write_properties = prune_properties(
            payload["requestData"]["resourceProperties"], self.write_only_paths
        )

        previous_request_without_write_properties = None
        if payload["requestData"]["previousResourceProperties"]:
            previous_request_without_write_properties = prune_properties(
                payload["requestData"]["previousResourceProperties"],
                self.write_only_paths,
            )
        payload_to_log = {
            "callbackContext": payload["callbackContext"],
            "action": payload["action"],
            "requestData": {
                "resourceProperties": request_without_write_properties,
                "previousResourceProperties": previous_request_without_write_properties,
                "logicalResourceId": payload["requestData"]["logicalResourceId"],
            },
            "region": payload["region"],
            "awsAccountId": payload["awsAccountId"],
            "bearerToken": payload["bearerToken"],
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
                )
                .decode()
                .strip()
            )
            LOG.debug("=== Handler execution logs ===")
            LOG.debug(result)
            # pylint: disable=W1401
            regex = "__CFN_RESOURCE_START_RESPONSE__([\s\S]*)__CFN_RESOURCE_END_RESPONSE__"  # noqa: W605,B950 # pylint: disable=C0301
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
        LOG.debug("Received response\n%s", payload)
        return payload

    def call_and_assert(
        self, action, assert_status, current_model, previous_model=None, **kwargs
    ):
        if assert_status not in [OperationStatus.SUCCESS, OperationStatus.FAILED]:
            raise ValueError("Assert status {} not supported.".format(assert_status))

        status, response = self.call(action, current_model, previous_model, **kwargs)
        if assert_status == OperationStatus.SUCCESS:
            self.assert_success(status, response)
            error_code = None
        else:
            error_code = self.assert_failed(status, response)
        return status, response, error_code

    def call(self, action, current_model, previous_model=None, **kwargs):
        request = self._make_payload(action, current_model, previous_model, **kwargs)
        start_time = time.time()
        response = self._call(request)
        self.assert_time(start_time, time.time(), action)

        # this throws a KeyError if status isn't present, or if it isn't a valid status
        status = OperationStatus[response["status"]]

        if action in (Action.READ, Action.LIST):
            assert status != OperationStatus.IN_PROGRESS
            return status, response

        while status == OperationStatus.IN_PROGRESS:
            callback_delay_seconds = self.assert_in_progress(status, response)
            self.assert_primary_identifier(
                self.primary_identifier_paths, response.get("resourceModel")
            )
            sleep(callback_delay_seconds)

            request["requestData"]["resourceProperties"] = response.get("resourceModel")
            request["callbackContext"] = response.get("callbackContext")

            response = self._call(request)
            status = OperationStatus[response["status"]]

        # ensure writeOnlyProperties are not returned on final responses
        if "resourceModel" in response.keys() and status == OperationStatus.SUCCESS:
            self.assert_write_only_property_does_not_exist(response["resourceModel"])

        return status, response

    def has_update_handler(self):
        return "update" in self._schema["handlers"]
