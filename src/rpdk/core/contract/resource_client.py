# pylint: disable=import-outside-toplevel
import json
import logging
from time import sleep
from uuid import uuid4

from botocore import UNSIGNED
from botocore.config import Config

from rpdk.core.contract.interface import Action, HandlerErrorCode, OperationStatus

from ..boto_helpers import (
    LOWER_CAMEL_CRED_KEYS,
    create_sdk_session,
    get_temporary_credentials,
)
from ..jsonutils.pointer import fragment_decode
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
        self, function_name, endpoint, region, schema, overrides, role_arn=None
    ):  # pylint: disable=too-many-arguments
        self._schema = schema
        self._session = create_sdk_session(region)
        self._creds = get_temporary_credentials(
            self._session, LOWER_CAMEL_CRED_KEYS, role_arn
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
        self._overrides = overrides
        self._update_schema(schema)

    def _properties_to_paths(self, key):
        return {fragment_decode(prop, prefix="") for prop in self._schema.get(key, [])}

    def _update_schema(self, schema):
        # TODO: resolve $ref
        self._schema = schema
        self._strategy = None
        self._update_strategy = None

        self._primary_identifier_paths = self._properties_to_paths("primaryIdentifier")
        self.read_only_paths = self._properties_to_paths("readOnlyProperties")
        self._write_only_paths = self._properties_to_paths("writeOnlyProperties")
        self._create_only_paths = self._properties_to_paths("createOnlyProperties")

        additional_identifiers = self._schema.get("additionalIdentifiers", [])
        self._additional_identifiers_paths = [
            {fragment_decode(prop, prefix="") for prop in identifier}
            for identifier in additional_identifiers
        ]

    def has_writable_identifier(self):
        for path in self._primary_identifier_paths:
            if path not in self.read_only_paths:
                return True
        for identifier_paths in self._additional_identifiers_paths:
            for path in identifier_paths:
                if path not in self.read_only_paths:
                    return True
        return False

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
    def update_strategy(self):
        # an empty strategy (i.e. false-y) is valid
        if self._update_strategy is not None:
            return self._update_strategy

        # imported here to avoid hypothesis being loaded before pytest is loaded
        from .resource_generator import ResourceGenerator

        # make a copy so the original schema is never modified
        schema = json.loads(json.dumps(self._schema))

        prune_properties(schema, self.read_only_paths)
        prune_properties(schema, self._create_only_paths)

        self._update_strategy = ResourceGenerator(schema).generate_schema_strategy(
            schema
        )
        return self._update_strategy

    def generate_create_example(self):
        example = self.strategy.example()
        return override_properties(example, self._overrides.get("CREATE", {}))

    def generate_update_example(self, create_model):
        overrides = self._overrides.get("UPDATE", self._overrides.get("CREATE", {}))
        example = override_properties(self.update_strategy.example(), overrides)
        return {**create_model, **example}

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
        assert (
            response.get("callbackContext") is None
        ), "SUCCESS events should not return a callback context"

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
            response.get("resourceModel") is None
        ), "FAILED events should not include a resource model"
        assert (
            response.get("resourceModels") is None
        ), "FAILED events should not include any resource models"
        assert (
            response.get("callbackContext") is None
        ), "FAILED events should not return a callback context"

        return error_code

    @staticmethod
    def make_request(desired_resource_state, previous_resource_state, **kwargs):
        return {
            "desiredResourceState": desired_resource_state,
            "previousResourceState": previous_resource_state,
            "logicalResourceIdentifier": None,
            **kwargs,
        }

    @staticmethod
    def generate_token():
        return str(uuid4())

    def _make_payload(self, action, request):
        return {
            "credentials": self._creds.copy(),
            "action": action,
            "request": {"clientRequestToken": self.generate_token(), **request},
            "callbackContext": None,
        }

    def _call(self, payload):
        payload = json.dumps(payload, ensure_ascii=False, indent=2)
        LOG.debug("Sending request\n%s", payload)
        result = self._client.invoke(
            FunctionName=self._function_name, Payload=payload.encode("utf-8")
        )
        payload = json.load(result["Payload"])
        LOG.debug("Received response\n%s", payload)
        return payload

    def call_and_assert(
        self, action, assert_status, current_model, previous_model=None, **kwargs
    ):
        if assert_status not in [OperationStatus.SUCCESS, OperationStatus.FAILED]:
            raise ValueError("Assert status {} not supported.".format(assert_status))
        request = self.make_request(current_model, previous_model, **kwargs)
        status, response = self.call(action, request)
        if assert_status == OperationStatus.SUCCESS:
            self.assert_success(status, response)
            error_code = None
        else:
            error_code = self.assert_failed(status, response)
        return status, response, error_code

    def call(self, action, request):
        payload = self._make_payload(action, request)
        response = self._call(payload)

        # this throws a KeyError if status isn't present, or if it isn't a valid status
        status = OperationStatus[response["status"]]

        if action in (Action.READ, Action.LIST):
            return status, response

        while status == OperationStatus.IN_PROGRESS:
            callback_delay_seconds = self.assert_in_progress(status, response)
            sleep(callback_delay_seconds)

            payload["callbackContext"] = response.get("callbackContext")
            response = self._call(payload)
            status = OperationStatus[response["status"]]

        return status, response

    def has_update_handler(self):
        return "update" in self._schema["handlers"]
