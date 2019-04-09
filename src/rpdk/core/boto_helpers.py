import logging

from boto3 import Session as Boto3Session

from .exceptions import CLIMisconfiguredError

LOG = logging.getLogger(__name__)


def create_sdk_session():
    def _known_error(msg):
        raise CLIMisconfiguredError(
            msg + ". Please ensure your AWS CLI is configured correctly: "
            "https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html"
        )

    session = Boto3Session()

    if session.region_name is None:
        _known_error("No region specified")

    if session.get_credentials() is None:
        _known_error("No credentials specified")

    return session
