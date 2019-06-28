import logging

from boto3 import Session as Boto3Session

from .exceptions import CLIMisconfiguredError

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


def get_temporary_credentials(session, key_names=BOTO_CRED_KEYS):
    frozen = session.get_credentials().get_frozen_credentials()
    if frozen.token:
        creds = (frozen.access_key, frozen.secret_key, frozen.token)
    else:
        sts_client = session.client("sts")
        response = sts_client.get_session_token()
        temp = response["Credentials"]
        creds = (temp["AccessKeyId"], temp["SecretAccessKey"], temp["SessionToken"])
    return dict(zip(key_names, creds))
