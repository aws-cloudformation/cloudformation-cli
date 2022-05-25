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
from rpdk.core.contract.type_configuration import TypeConfiguration
from rpdk.core.exceptions import InvalidProjectError

from ..boto_helpers import (
    LOWER_CAMEL_CRED_KEYS,
    create_sdk_session,
    get_account,
    get_temporary_credentials,
)
from ..jsonutils.pointer import fragment_decode, fragment_list
from ..jsonutils.utils import (
    UNPACK_SEQUENCE_IDENTIFIER,
    item_hash,
    traverse,
    traverse_path_for_sequence_members,
    traverse_raw_schema,
)

LOG = logging.getLogger(__name__)
LOOKUP_ERROR_MESSAGE_FORMAT = (
    "Caught LookupError when pruning properties for document %s and path %s"
)


def prune_properties(document, paths):
    """Prune given properties from a document.

    This assumes properties will always have an object (dict) as a parent.
    The function modifies the document in-place, but also returns the document
    for convenience. (The return value may be ignored.)
    """
    for path in paths:
        # if '*' is in path, we need to prune more than one property (prune property for all members of array)
        if UNPACK_SEQUENCE_IDENTIFIER in path:
            document = _prune_properties_for_all_sequence_members(document, path)
            continue
        try:
            _prop, resolved_path, parent = traverse(document, path)
        except LookupError:
            # not found means nothing to delete
            LOG.info(LOOKUP_ERROR_MESSAGE_FORMAT, document, path)
        else:
            key = resolved_path[-1]
            del parent[key]
    return document


def _prune_properties_for_all_sequence_members(document: dict, path: list) -> dict:
    try:
        # this returns multiple paths
        _prop, resolved_paths = traverse_path_for_sequence_members(document, path)
    except LookupError:
        # not found means nothing to delete
        LOG.info(LOOKUP_ERROR_MESSAGE_FORMAT, document, path)
    else:
        # paths with indices are gathered in increasing order, but we need to prune in reverse order
        resolved_paths = resolved_paths[::-1]
        for resolved_path in resolved_paths:
            new_doc = document
            for key in resolved_path[: len(resolved_path) - 1]:
                new_doc = new_doc[key]
            key = resolved_path[-1]
            del new_doc[key]
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


def prune_properties_which_dont_exist_in_path(model, paths):
    """Prunes model to properties present in path. This method removes any property
    from the model which does not exists in the paths

    This assumes properties will always have an object (dict) as a parent.
    The function returns the model after pruning all but the path which exists
    in the paths tuple from the input_model
    """
    document = {"properties": model.copy()}
    for model_path in model.keys():
        path_tuple = ("properties", model_path)
        if path_tuple not in paths:
            _prop, resolved_path, parent = traverse(document, path_tuple)
            key = resolved_path[-1]
            del parent[key]
    return document["properties"]


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
        type_name=None,
        log_group_name=None,
        log_role_arn=None,
        docker_image=None,
        executable_entrypoint=None,
    ):  # pylint: disable=too-many-arguments
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
                    read_timeout=15 * 60,
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
            or any(
                self.is_property_in_path(k, additional_identifier_paths)
                for additional_identifier_paths in self._additional_identifiers_paths
            )
        }

    @staticmethod
    def is_property_in_path(key, paths):
        for path in paths:
            prop = fragment_list(path, "properties")[0]
            if prop == key:
                return True
        return False

    @staticmethod
    def get_value_by_key_path(model, key_path):
        if isinstance(key_path, (tuple, list)):
            value = model
            for path in key_path:
                value = value[path]
            return value
        return model[key_path]

    def validate_update_example_keys(self, unique_identifiers, update_example):
        for primary_identifier in self.primary_identifier_paths:
            if primary_identifier in self.create_only_paths:
                primary_key_path = fragment_list(primary_identifier, "properties")
                update_example_pk_value = self.get_value_by_key_path(
                    update_example, primary_key_path
                )
                unique_identifiers_pk_value = self.get_value_by_key_path(
                    unique_identifiers, primary_key_path
                )
                assert update_example_pk_value == unique_identifiers_pk_value, (
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
            create_model_with_read_only_properties = (
                prune_properties_which_dont_exist_in_path(
                    create_model, self.read_only_paths
                )
            )
            return {**create_model_with_read_only_properties, **update_example}

        overrides = self._overrides.get("UPDATE", self._overrides.get("CREATE", {}))
        example = override_properties(self.update_strategy.example(), overrides)
        return {**create_model, **example}

    def generate_invalid_update_example(self, create_model):
        if self._inputs:
            return self._inputs["INVALID"]
        overrides = self._overrides.get("UPDATE", self._overrides.get("CREATE", {}))
        example = override_properties(self.invalid_strategy.example(), overrides)
        return {**create_model, **example}

    def compare(self, inputs, outputs, path=()):
        assertion_error_message = (
            "All properties specified in the request MUST "
            "be present in the model returned, and they MUST"
            " match exactly, with the exception of properties"
            " defined as writeOnlyProperties in the resource schema"
        )
        try:
            if isinstance(inputs, dict):
                for key in inputs:
                    new_path = path + (key,)
                    if isinstance(inputs[key], dict):
                        self.compare(inputs[key], outputs[key], new_path)
                    elif isinstance(inputs[key], list):
                        assert len(inputs[key]) == len(outputs[key])

                        is_ordered = traverse_raw_schema(self._schema, new_path).get(
                            "insertionOrder", True
                        )

                        self.compare_collection(
                            inputs[key], outputs[key], is_ordered, new_path
                        )
                    else:
                        assert inputs[key] == outputs[key], assertion_error_message
            else:
                assert inputs == outputs, assertion_error_message
        except Exception as exception:
            raise AssertionError(assertion_error_message) from exception

    def compare_collection(self, inputs, outputs, is_ordered, path):
        if is_ordered:
            for index in range(len(inputs)):  # pylint: disable=C0200
                self.compare(inputs[index], outputs[index], path)
            return

        assert {item_hash(item) for item in inputs} == {
            item_hash(item) for item in outputs
        }

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
        type_name,
        log_group_name,
        log_creds,
        token,
        callback_context=None,
        type_configuration=None,
        **kwargs,
    ):
        request_body = {
            "requestData": {
                "callerCredentials": creds,
                "resourceProperties": desired_resource_state,
                "previousResourceProperties": previous_resource_state,
                "logicalResourceId": token,
                "typeConfiguration": type_configuration,
            },
            "region": region,
            "awsAccountId": account,
            "action": action,
            "callbackContext": callback_context,
            "bearerToken": token,
            "resourceType": type_name,
            **kwargs,
        }
        if log_group_name and log_creds:
            request_body["requestData"]["providerCredentials"] = log_creds
            request_body["requestData"]["providerLogGroupName"] = log_group_name
        return request_body

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

    def _make_payload(
        self,
        action,
        current_model,
        previous_model=None,
        type_configuration=None,
        **kwargs,
    ):
        return self.make_request(
            current_model,
            previous_model,
            self.region,
            self.account,
            action,
            get_temporary_credentials(
                self._session, LOWER_CAMEL_CRED_KEYS, self._role_arn
            ),
            self._type_name,
            self._log_group_name,
            get_temporary_credentials(
                self._session, LOWER_CAMEL_CRED_KEYS, self._log_role_arn
            ),
            self.generate_token(),
            type_configuration=type_configuration,
            **kwargs,
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
        if not self.has_required_handlers():
            raise ValueError("Create/Read/Delete handlers are required")
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
        request = self._make_payload(
            action,
            current_model,
            previous_model,
            TypeConfiguration.get_type_configuration(),
            **kwargs,
        )
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
            # refresh credential for every handler invocation
            request["requestData"]["callerCredentials"] = get_temporary_credentials(
                self._session, LOWER_CAMEL_CRED_KEYS, self._role_arn
            )

            response = self._call(request)
            status = OperationStatus[response["status"]]

        # ensure writeOnlyProperties are not returned on final responses
        if "resourceModel" in response.keys() and status == OperationStatus.SUCCESS:
            self.assert_write_only_property_does_not_exist(response["resourceModel"])

        return status, response

    def has_update_handler(self):
        return "update" in self._schema["handlers"]

    def contains_tagging_metadata(self):
        return "tagging" in self._schema

    def is_taggable(self):
        try:
            return self._schema["tagging"]["taggable"]
        except KeyError:
            try:
                return self._schema["taggable"]
            except KeyError:
                return True

    def is_tag_updatable(self):
        try:
            return self._schema["tagging"]["tagUpdatable"]
        except KeyError:
            return self.is_taggable()

    def metadata_contains_tag_property(self):
        try:
            return "tagProperty" in self._schema["tagging"]
        except KeyError:
            return False

    def validate_model_contain_tags(self, inputs):
        assertion_error_message = "Contract test inputs does not contain tags property."
        try:
            tag_property_path = self._schema["tagging"]["tagProperty"]
        except KeyError:
            tag_property_path = "/properties/Tags"
        tag_property_name = tag_property_path.split("/")[-1]
        LOG.debug("Defined tag property name is: %s\n", tag_property_name)
        try:
            if isinstance(inputs, dict):
                for key in inputs:
                    if key == tag_property_name:
                        return True
            else:
                raise assertion_error_message
        except Exception as exception:
            raise AssertionError(assertion_error_message) from exception
        return False

    def has_required_handlers(self):
        try:
            has_delete = "delete" in self._schema["handlers"]
            has_create = "create" in self._schema["handlers"]
            has_read = "read" in self._schema["handlers"]
            return has_read and has_create and has_delete
        except KeyError:
            return False
