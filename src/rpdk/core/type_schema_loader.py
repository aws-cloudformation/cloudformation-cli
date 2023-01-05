import collections.abc
import json
import logging
import os
import re
from urllib.parse import urlparse

import requests
from botocore.exceptions import ClientError
from requests.exceptions import RequestException

from .exceptions import DownstreamError, InvalidTypeSchemaError

LOG = logging.getLogger(__name__)

REGISTRY_RESOURCE_TYPE = "RESOURCE"
REGISTRY_DEPRECATED_STATUS_LIVE = "LIVE"
REGISTRY_VISIBILITY_PRIVATE = "PRIVATE"
REGISTRY_VISIBILITY_PUBLIC = "PUBLIC"
REGISTRY_RESULTS_PAGE_SIZE = 100
VALID_TYPE_SCHEMA_URI_REGEX = "^(https?|file|s3)://.+$"


def is_valid_type_schema_uri(uri):
    if uri is None:
        return False

    pattern = re.compile(VALID_TYPE_SCHEMA_URI_REGEX)
    return bool(re.search(pattern, uri))


class TypeSchemaLoader:
    """
    This class is constructed to return schema of the target resource type
    There are four options:
        * Reads the schema from a JSON file
        * Reads the schema from a provided url
        * Reads the schema from file in a S3 bucket
        * Calls CFN DescribeType API to retrieve the schema
    """

    def __init__(self, cfn_client, s3_client, local_only=False):
        self.cfn_client = cfn_client
        self.s3_client = s3_client
        self.local_only = local_only

    def load_type_info(self, type_names, local_schemas=None, local_info=None):
        if local_info is None:
            local_info = {}

        schemas = self._validate_and_load_local_schemas(local_schemas)

        type_info = {}
        for type_name in type_names:
            LOG.debug("Retrieving info for type: %s", type_name)

            target_info = {
                "TypeName": type_name,
                "TargetName": type_name,
                "TargetType": REGISTRY_RESOURCE_TYPE,
            }

            if type_name in schemas or type_name in local_info:
                LOG.warning(
                    "Loading type info for %s from provided local info", type_name
                )
                if type_name in schemas and type_name in local_info:
                    target_info.update(local_info[type_name])
                    if "Schema" in target_info:
                        if target_info["Schema"] != schemas[type_name]:
                            raise InvalidTypeSchemaError(
                                f"Duplicate conflicting schemas for '{type_name}' target type in 'target-info.json' "
                                f"file and 'target-schemas' directory. "
                            )
                    else:
                        target_info["Schema"] = schemas[type_name]
                else:
                    if type_name in local_info:
                        target_info.update(local_info[type_name])
                    else:
                        target_info["Schema"] = schemas[type_name]

                if "Schema" not in target_info or not target_info.get("Schema"):
                    raise InvalidTypeSchemaError(
                        f"No local schema provided for '{type_name}' target type."
                    )
            elif self.local_only:
                LOG.warning(
                    "Attempting to load local type info %s with incorrect configuration. Local target schema file or "
                    "'target-info.json' are required to load local target info",
                    type_name,
                )
                raise InvalidTypeSchemaError(
                    "Local type schema or 'target-info.json' are required to load local type info"
                )
            else:
                target_info.update(
                    self.describe_type(TypeName=type_name, Type=REGISTRY_RESOURCE_TYPE)
                )

            target_info[
                "IsCfnRegistrySupportedType"
            ] = True  # For backwards compatibility
            target_info["SchemaFileAvailable"] = bool(target_info.get("Schema"))

            type_info[type_name] = target_info

        return type_info

    def load_type_schemas(self, schemas=None):
        if not schemas:
            schemas = []

        type_schemas = {}
        for schema in schemas:
            loaded_type_schema = self.load_type_schema(schema)

            if isinstance(loaded_type_schema, collections.abc.Mapping):
                loaded_schemas = [loaded_type_schema]
            else:
                loaded_schemas = loaded_type_schema

            for loaded_schema in loaded_schemas:
                try:
                    type_name = loaded_schema["typeName"]
                    if (
                        type_name in type_schemas
                        and loaded_schema != type_schemas[type_name]
                    ):
                        raise InvalidTypeSchemaError(
                            f"Duplicate schemas for '{type_name}' target type."
                        )

                    type_schemas[type_name] = loaded_schema
                except (KeyError, TypeError) as e:
                    LOG.warning(
                        "Error while loading a provided schema: %s", schema, exc_info=e
                    )
                    raise InvalidTypeSchemaError(
                        "Unknown error while loading type schema"
                    ) from e

        return type_schemas

    def load_type_schema(self, type_schema):
        if isinstance(type_schema, collections.abc.Mapping):
            schema = type_schema
        elif self._is_json(type_schema):
            schema = self.load_type_schema_from_json(type_schema)
        elif os.path.isfile(type_schema):
            schema = self.load_type_schema_from_file(type_schema)
        elif is_valid_type_schema_uri(type_schema):
            schema = self.load_type_schema_from_uri(type_schema)
        else:
            raise InvalidTypeSchemaError(
                f"Provided schema is invalid or not supported: {type_schema}"
            )

        return schema

    def _validate_and_load_local_schemas(self, local_schemas):
        if local_schemas is None:
            schemas = {}
        elif isinstance(local_schemas, collections.abc.Mapping):
            schemas = local_schemas
        elif isinstance(local_schemas, (str, bytes, bytearray)):
            schemas = self.load_type_schemas(
                [
                    local_schemas
                    if isinstance(local_schemas, str)
                    else str(local_schemas, "utf-8")
                ]
            )
        elif isinstance(local_schemas, collections.abc.Collection):
            schemas = self.load_type_schemas(local_schemas)
        else:
            raise InvalidTypeSchemaError(
                "Local Schemas must be either list of schemas to load or mapping of type names to schemas"
            )

        return schemas

    @staticmethod
    def load_type_schema_from_json(schema_json):
        try:
            return json.loads(schema_json)
        except json.JSONDecodeError as e:
            LOG.debug("Provided schema is not valid JSON", exc_info=e)
            raise InvalidTypeSchemaError("Schema is not valid JSON") from e

    def load_type_schema_from_uri(self, schema_uri):
        LOG.info("Loading schema from URI: %s", schema_uri)
        if not is_valid_type_schema_uri(schema_uri):
            raise InvalidTypeSchemaError(
                f"URI provided {schema_uri} is not supported or invalid."
            )

        uri = urlparse(schema_uri)
        if self.local_only and uri.scheme != "file":
            raise InvalidTypeSchemaError(f"URI provided is not local: {schema_uri}")

        if uri.scheme == "file":
            type_schema = self.load_type_schema_from_file(uri.path)
        elif uri.scheme == "https":
            type_schema = self._get_type_schema_from_url(uri.geturl())
        elif uri.scheme == "s3":
            bucket = uri.netloc
            key = uri.path.lstrip("/")
            type_schema = self._get_type_schema_from_s3(bucket, key)
        else:  # pragma: no cover
            LOG.debug(
                "URI provided '%s' is not supported or invalid",
                schema_uri,
            )
            raise InvalidTypeSchemaError(
                f"URI provided {schema_uri} is not supported or invalid."
            )

        return type_schema

    @staticmethod
    def load_type_schema_from_file(schema_path):
        try:
            with open(schema_path, "r") as file:
                return TypeSchemaLoader.load_type_schema_from_json(file.read())
        except FileNotFoundError as e:
            LOG.debug("Target schema file '%s' not found", schema_path, exc_info=e)
            raise InvalidTypeSchemaError(
                f"Target schema file '{schema_path}' not found"
            ) from e

    @staticmethod
    def _get_type_schema_from_url(url):
        try:
            response = requests.get(url, timeout=60)
            if response.status_code != 200:
                response.raise_for_status()

            return TypeSchemaLoader.load_type_schema_from_json(
                response.content.decode("utf-8")
            )
        except RequestException as e:
            LOG.debug("Unknown error when calling url '%s'", url, exc_info=e)
            raise DownstreamError("Unknown error while making HTTP request") from e

    def _get_type_schema_from_s3(self, bucket, key):
        try:
            type_schema = (
                self.s3_client.get_object(Bucket=bucket, Key=key)["Body"]
                .read()
                .decode("utf-8")
            )
            return self.load_type_schema_from_json(type_schema)
        except ClientError as err:
            LOG.debug(
                "Getting S3 object in bucket '%s' with key '%s' resulted in unknown ClientError",
                bucket,
                key,
                exc_info=err,
            )
            raise DownstreamError("Error getting S3 object from bucket") from err

    def load_schema_from_cfn_registry(self, type_name, extension_type):
        return self.describe_type(TypeName=type_name, Type=extension_type)["Schema"]

    def describe_type(self, **kwargs):
        try:
            res = self.cfn_client.describe_type(**kwargs)

            res.pop("LastUpdated", None)
            res.pop("TimeCreated", None)
            res.pop("ResponseMetadata", None)
            res["Schema"] = (
                json.loads(res["Schema"])
                if not isinstance(res["Schema"], dict)
                else res["Schema"]
            )

            return res
        except ClientError as e:
            LOG.debug("Describing type resulted in unknown ClientError", exc_info=e)
            raise DownstreamError("Unknown CloudFormation error") from e

    @staticmethod
    def _is_json(data):
        if not isinstance(data, (str, bytes, bytearray)):
            return False
        data = data if isinstance(data, str) else str(data, "utf-8")
        return (data.startswith("{") and data.endswith("}")) or (
            data.startswith("[") and data.endswith("]")
        )
