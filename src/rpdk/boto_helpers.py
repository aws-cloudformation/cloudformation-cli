import logging

from boto3 import Session as Boto3Session
from botocore.session import Session as BotocoreSession

LOG = logging.getLogger(__name__)


def _create_sdk_session():
    def _known_error(msg):
        LOG.critical(
            "%s. Please ensure your AWS CLI is configured correctly: "
            "https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html",
            msg,
        )
        raise SystemExit(1)

    botocore_session = BotocoreSession()
    boto3_session = Boto3Session(
        botocore_session=botocore_session,
        # https://github.com/awslabs/aws-cloudformation-rpdk/issues/173
        region_name="us-west-2",
    )

    if boto3_session.region_name is None:
        _known_error("No region specified")

    if boto3_session.get_credentials() is None:
        _known_error("No credentials specified")

    return boto3_session, botocore_session


def create_client(name, **kwargs):
    boto3_session, botocore_session = _create_sdk_session()
    # https://github.com/awslabs/aws-cloudformation-rpdk/issues/173
    if name == "cloudformation":
        kwargs["endpoint_url"] = "https://uluru-facade.us-west-2.amazonaws.com"
    client = boto3_session.client(name, **kwargs)
    client.boto3_session = boto3_session
    client.botocore_session = botocore_session
    return client
