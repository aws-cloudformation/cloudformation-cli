import json
import logging
import os
import re
from urllib.parse import urlparse

import requests
from botocore.exceptions import ClientError

from .boto_helpers import create_sdk_session
from .exceptions import RPDKBaseException

LOG = logging.getLogger(__name__)

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

    @staticmethod
    def get_type_schema_loader(endpoint_url=None, region_name=None):
        cfn_client = None
        s3_client = None
        try:
            session = create_sdk_session(region_name)
            cfn_client = session.client("cloudformation", endpoint_url=endpoint_url)
            s3_client = session.client("s3", endpoint_url=endpoint_url)
        except RPDKBaseException as err:  # pragma: no cover
            LOG.debug("Type schema loader setup resulted in error", exc_info=err)

        return TypeSchemaLoader(cfn_client, s3_client)

    def __init__(self, cfn_client, s3_client):
        self.cfn_client = cfn_client
        self.s3_client = s3_client

    def load_type_schema(self, provided_schema, default_schema=None):
        if not provided_schema:
            return default_schema

        if provided_schema.startswith("{") and provided_schema.endswith("}"):
            type_schema = self.load_type_schema_from_json(
                provided_schema, default_schema
            )
        elif provided_schema.startswith("[") and provided_schema.endswith("]"):
            type_schema = self.load_type_schema_from_json(
                provided_schema, default_schema
            )
        elif os.path.isfile(provided_schema):
            type_schema = self.load_type_schema_from_file(
                provided_schema, default_schema
            )
        elif is_valid_type_schema_uri(provided_schema):
            type_schema = self.load_type_schema_from_uri(
                provided_schema, default_schema
            )
        else:
            type_schema = default_schema

        return type_schema

    @staticmethod
    def load_type_schema_from_json(schema_json, default_schema=None):
        if not schema_json:
            return default_schema

        try:
            return json.loads(schema_json)
        except json.JSONDecodeError:
            LOG.debug(
                "Provided schema is not valid JSON. Falling back to default schema."
            )
            return default_schema

    def load_type_schema_from_uri(self, schema_uri, default_schema=None):
        if not is_valid_type_schema_uri(schema_uri):
            return default_schema

        uri = urlparse(schema_uri)
        if uri.scheme == "file":
            type_schema = self.load_type_schema_from_file(uri.path, default_schema)
        elif uri.scheme == "https":
            type_schema = self._get_type_schema_from_url(uri.geturl(), default_schema)
        elif uri.scheme == "s3":
            bucket = uri.netloc
            key = uri.path.lstrip("/")
            type_schema = self._get_type_schema_from_s3(bucket, key, default_schema)
        else:
            LOG.debug(
                "URI provided '%s' is not supported. Falling back to default schema",
                schema_uri,
            )
            type_schema = default_schema

        return type_schema

    @staticmethod
    def load_type_schema_from_file(schema_path, default_schema=None):
        if not schema_path:
            return default_schema

        try:
            with open(schema_path, "r") as file:
                return TypeSchemaLoader.load_type_schema_from_json(file.read())
        except FileNotFoundError:
            LOG.debug(
                "Target schema file '%s' not found. Falling back to default schema.",
                schema_path,
            )
            return default_schema

    @staticmethod
    def _get_type_schema_from_url(url, default_schema=None):
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            type_schema = TypeSchemaLoader.load_type_schema_from_json(
                response.content.decode("utf-8")
            )
        else:
            LOG.debug(
                "Received status code of '%s' when calling url '%s.'",
                str(response.status_code),
                url,
            )
            LOG.debug("Falling back to default schema.")
            type_schema = default_schema

        return type_schema

    def _get_type_schema_from_s3(self, bucket, key, default_schema=None):
        if self.s3_client is None:  # pragma: no cover
            LOG.debug("S3 client is not set up")
            LOG.debug("Falling back to default schema")
            return default_schema

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
            LOG.debug("Falling back to default schema")
            return default_schema

    def load_schema_from_cfn_registry(
        self, type_name, extension_type, default_schema=None
    ):
        if self.cfn_client is None:  # pragma: no cover
            LOG.debug("CloudFormation client is not set up")
            LOG.debug("Falling back to default schema for type '%s'", type_name)
            return default_schema, None, None

        try:
            response = self.cfn_client.describe_type(
                Type=extension_type, TypeName=type_name
            )
            return (
                self.load_type_schema_from_json(response["Schema"]),
                response["Type"],
                response["ProvisioningType"],
            )
        except ClientError as err:
            LOG.debug(
                "Describing type '%s' resulted in unknown ClientError",
                type_name,
                exc_info=err,
            )
            LOG.debug("Falling back to default schema for type '%s'", type_name)
            return default_schema, None, None

    def get_provision_type(self, type_name, extension_type):
        if self.cfn_client is None:  # pragma: no cover
            LOG.debug("CloudFormation client is not set up")
            return None

        try:
            return self.cfn_client.describe_type(
                Type=extension_type, TypeName=type_name
            )["ProvisioningType"]
        except ClientError as err:
            LOG.debug(
                "Describing type '%s' resulted in unknown ClientError",
                type_name,
                exc_info=err,
            )
            return None
