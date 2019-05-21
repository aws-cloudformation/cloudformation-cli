from unittest.mock import patch

import pytest

from rpdk.core.boto_helpers import create_sdk_session
from rpdk.core.exceptions import CLIMisconfiguredError


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
