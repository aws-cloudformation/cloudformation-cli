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
    """Prune all properties from a document.

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


class ResourceClient:  # pylint: disable=too-many-instance-attributes
    def __init__(self, function_name, endpoint, region, schema):
        self._session = create_sdk_session(region)
        self._creds = get_temporary_credentials(self._session, LOWER_CAMEL_CRED_KEYS)
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
                    read_timeout=60,
                    retries={"max_attempts": 0},
                    region_name=self._session.region_name,
                ),
            )
        else:
            self._client = self._session.client("lambda", endpoint_url=endpoint)

        # TODO: resolve $ref
        self._schema = schema
        self._strategy = None

        self._primary_identifier_paths = {
            fragment_decode(prop, prefix="")
            for prop in self._schema.get("primaryIdentifier", [])
        }
        self._read_only_paths = {
            fragment_decode(prop, prefix="")
            for prop in self._schema.get("readOnlyProperties", [])
        }
        self._write_only_paths = {
            fragment_decode(prop, prefix="")
            for prop in self._schema.get("writeOnlyProperties", [])
        }
        self._create_only_paths = {
            fragment_decode(prop, prefix="")
            for prop in self._schema.get("createOnlyProperties", [])
        }

    @property
    def strategy(self):
        # an empty strategy (i.e. false-y) is valid
        if self._strategy is not None:
            return self._strategy

        # imported here to avoid hypothesis being loaded before pytest is loaded
        from .resource_generator import generate_schema_strategy

        self._strategy = generate_schema_strategy(self._schema)
        return self._strategy

    def generate_create_example(self):
        return prune_properties(self.strategy.example(), self._read_only_paths)

    @staticmethod
    def assert_in_progress(status, response):
        assert status == OperationStatus.IN_PROGRESS, "status should be IN_PROGRESS"
        assert (
            response.get("errorCode", 0) == 0
        ), "IN_PROGRESS events should have no error code set"
        assert (
            "callbackDelaySeconds" in response
        ), "IN_PROGRESS events must include a callback delay"
        assert (
            response.get("message") is None
        ), "IN_PROGRESS events should not include a message"
        assert (
            response.get("resourceModel") is None
        ), "IN_PROGRESS events should not include a resource model"
        assert (
            response.get("resourceModels") is None
        ), "IN_PROGRESS events should not include any resource models"

        return response["callbackDelaySeconds"]

    @staticmethod
    def assert_success(status, response):
        assert status == OperationStatus.SUCCESS, "status should be SUCCESS"
        assert (
            response.get("errorCode", 0) == 0
        ), "SUCCESS events should have no error code set"
        assert (
            response.get("callbackDelaySeconds", 0) == 0
        ), "SUCCESS events should have no callback delay"
        # assert response.get("callbackContext") is None

    @staticmethod
    def assert_failed(status, response):
        assert status == OperationStatus.FAILED, "status should be FAILED"
        assert "errorCode" in response, "FAILED events must have an error code set"
        assert (
            response.get("callbackDelaySeconds", 0) == 0
        ), "FAILED events should have no callback delay"
        assert (
            response.get("resourceModel") is None
        ), "FAILED events should not include a resource model"
        assert (
            response.get("resourceModels") is None
        ), "FAILED events should not include any resource models"
        # assert response.get("callbackContext") is None

        return HandlerErrorCode[response["errorCode"]]

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
