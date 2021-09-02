import logging
from datetime import datetime

import botocore.loaders
import botocore.regions
from boto3 import Session as Boto3Session
from botocore.exceptions import ClientError

from .exceptions import CLIMisconfiguredError, DownstreamError

LOG = logging.getLogger(__name__)

BOTO_CRED_KEYS = ("aws_access_key_id", "aws_secret_access_key", "aws_session_token")
LOWER_CAMEL_CRED_KEYS = ("accessKeyId", "secretAccessKey", "sessionToken")


def create_sdk_session(region_name=None):
    def _known_error(msg):
        raise CLIMisconfiguredError(
            msg + ". Please ensure your AWS CLI is configured correctly: "
            "https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html"
        )

    session = Boto3Session(region_name=region_name)

    if session.region_name is None:
        _known_error("No region specified")

    if session.get_credentials() is None:
        _known_error("No credentials specified")

    return session


def get_temporary_credentials(session, key_names=BOTO_CRED_KEYS, role_arn=None):
    sts_client = session.client(
        "sts",
        endpoint_url=get_service_endpoint("sts", session.region_name),
        region_name=session.region_name,
    )
    if role_arn:
        session_name = "CloudFormationContractTest-{:%Y%m%d%H%M%S}".format(
            datetime.now()
        )
        try:
            response = sts_client.assume_role(
                RoleArn=role_arn, RoleSessionName=session_name, DurationSeconds=900
            )
        except ClientError:
            # pylint: disable=W1201
            LOG.debug(
                "Getting session token resulted in unknown ClientError. "
                + "Could not assume specified role '%s'.",
                role_arn,
            )
            raise DownstreamError() from Exception(
                "Could not assume specified role '{}'".format(role_arn)
            )
        temp = response["Credentials"]
        creds = (temp["AccessKeyId"], temp["SecretAccessKey"], temp["SessionToken"])
    else:
        frozen = session.get_credentials().get_frozen_credentials()
        if frozen.token:
            creds = (frozen.access_key, frozen.secret_key, frozen.token)
        else:
            try:
                response = sts_client.get_session_token(DurationSeconds=900)
            except ClientError as e:
                LOG.debug(
                    "Getting session token resulted in unknown ClientError", exc_info=e
                )
                raise DownstreamError("Could not retrieve session token") from e
            temp = response["Credentials"]
            creds = (temp["AccessKeyId"], temp["SecretAccessKey"], temp["SessionToken"])
    return dict(zip(key_names, creds))


def get_service_endpoint(service, region):
    loader = botocore.loaders.create_loader()
    data = loader.load_data("endpoints")
    resolver = botocore.regions.EndpointResolver(data)
    endpoint_data = resolver.construct_endpoint(service, region)
    return "https://" + endpoint_data["hostname"]


def get_account(session, temporary_credentials):
    sts_client = session.client(
        "sts",
        endpoint_url=get_service_endpoint("sts", session.region_name),
        region_name=session.region_name,
        aws_access_key_id=temporary_credentials["accessKeyId"],
        aws_secret_access_key=temporary_credentials["secretAccessKey"],
        aws_session_token=temporary_credentials["sessionToken"],
    )
    response = sts_client.get_caller_identity()
    return response.get("Account")
