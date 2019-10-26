from unittest.mock import ANY, create_autospec, patch

import pytest
from boto3 import Session
from botocore.exceptions import ClientError

from rpdk.core.boto_helpers import (
    BOTO_CRED_KEYS,
    LOWER_CAMEL_CRED_KEYS,
    create_sdk_session,
    get_temporary_credentials,
)
from rpdk.core.exceptions import CLIMisconfiguredError, DownstreamError

EXPECTED_ROLE = "someroleArn"


def test_create_sdk_session_region():
    patch_boto3 = patch("rpdk.core.boto_helpers.Boto3Session", autospec=True)

    with patch_boto3 as mock_boto3:
        mock_boto3.return_value.region_name = "us-east-1"
        boto3_session = create_sdk_session()

    assert boto3_session is mock_boto3.return_value

    mock_boto3.assert_called_once_with(region_name=None)
    mock_boto3.return_value.get_credentials.assert_called_once_with()


def test_create_sdk_session_no_region():
    patch_boto3 = patch("rpdk.core.boto_helpers.Boto3Session", autospec=True)

    with patch_boto3 as mock_boto3:
        mock_boto3.return_value.region_name = None
        with pytest.raises(CLIMisconfiguredError):
            create_sdk_session()

    mock_boto3.assert_called_once_with(region_name=None)


def test_create_sdk_session_no_creds():
    patch_boto3 = patch("rpdk.core.boto_helpers.Boto3Session", autospec=True)

    with patch_boto3 as mock_boto3:
        mock_boto3.return_value.region_name = "us-east-1"
        mock_boto3.return_value.get_credentials.return_value = None
        with pytest.raises(CLIMisconfiguredError):
            create_sdk_session()

    mock_boto3.assert_called_once_with(region_name=None)


def test_get_temporary_credentials_has_token():
    session = create_autospec(spec=Session, spec_set=True)
    frozen = session.get_credentials.return_value.get_frozen_credentials.return_value
    frozen.access_key = object()
    frozen.secret_key = object()
    frozen.token = object()

    creds = get_temporary_credentials(session)

    session.get_credentials.assert_called_once_with()
    session.client.assert_called_once_with("sts")

    assert len(creds) == 3
    assert tuple(creds.keys()) == BOTO_CRED_KEYS
    assert tuple(creds.values()) == (frozen.access_key, frozen.secret_key, frozen.token)


def test_get_temporary_credentials_needs_token():
    session = create_autospec(spec=Session, spec_set=True)
    frozen = session.get_credentials.return_value.get_frozen_credentials.return_value
    frozen.token = None

    access_key = object()
    secret_key = object()
    token = object()

    client = session.client.return_value
    client.get_session_token.return_value = {
        "Credentials": {
            "AccessKeyId": access_key,
            "SecretAccessKey": secret_key,
            "SessionToken": token,
        }
    }

    creds = get_temporary_credentials(session, LOWER_CAMEL_CRED_KEYS)

    session.get_credentials.assert_called_once_with()
    session.client.assert_called_once_with("sts")
    client.get_session_token.assert_called_once_with()

    assert len(creds) == 3
    assert tuple(creds.keys()) == LOWER_CAMEL_CRED_KEYS
    assert tuple(creds.values()) == (access_key, secret_key, token)


def test_get_temporary_credentials_invalid_credentials():
    session = create_autospec(spec=Session, spec_set=True)
    frozen = session.get_credentials.return_value.get_frozen_credentials.return_value
    frozen.token = None

    client = session.client.return_value
    client.get_session_token.side_effect = ClientError(
        {
            "Error": {
                "Type": "Sender",
                "Code": "InvalidClientTokenId",
                "Message": "The security token included in the request is invalid.",
            }
        },
        "GetSessionToken",
    )

    with pytest.raises(DownstreamError):
        get_temporary_credentials(session)

    session.get_credentials.assert_called_once_with()
    session.client.assert_called_once_with("sts")
    client.get_session_token.assert_called_once_with()


def test_get_temporary_credentials_assume_role_fails():
    session = create_autospec(spec=Session, spec_set=True)

    client = session.client.return_value
    client.assume_role.side_effect = ClientError(
        {
            "Error": {
                "Type": "Sender",
                "Code": "AccessDeniedException",
                "Message": "You do not have sufficient access to perform this action.",
            }
        },
        "GetSessionToken",
    )

    with pytest.raises(DownstreamError):
        get_temporary_credentials(session, role_arn=EXPECTED_ROLE)

    session.client.assert_called_once_with("sts")
    client.assume_role.assert_called_once_with(
        RoleArn=EXPECTED_ROLE, RoleSessionName=ANY
    )


def test_get_temporary_credentials_assume_role():
    session = create_autospec(spec=Session, spec_set=True)

    access_key = object()
    secret_key = object()
    token = object()

    client = session.client.return_value
    client.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": access_key,
            "SecretAccessKey": secret_key,
            "SessionToken": token,
        }
    }

    creds = get_temporary_credentials(session, LOWER_CAMEL_CRED_KEYS, EXPECTED_ROLE)

    session.client.assert_called_once_with("sts")
    client.assume_role.assert_called_once_with(
        RoleArn=EXPECTED_ROLE, RoleSessionName=ANY
    )

    assert len(creds) == 3
    assert tuple(creds.keys()) == LOWER_CAMEL_CRED_KEYS
    assert tuple(creds.values()) == (access_key, secret_key, token)
