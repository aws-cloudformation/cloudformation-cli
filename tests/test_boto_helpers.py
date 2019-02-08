from unittest.mock import Mock, patch

import pytest

from rpdk.core.boto_helpers import (
    _create_sdk_session,
    create_client,
    create_registry_client,
)


def test_create_client_lambda():
    mock_session = Mock(spec=["client"])
    botocore_session = object()
    with patch(
        "rpdk.core.boto_helpers._create_sdk_session", autospec=True
    ) as mock_create:
        mock_create.return_value = (mock_session, botocore_session)
        client = create_client("lambda", a="b")

    mock_create.assert_called_once_with()
    mock_session.client.assert_called_once_with("lambda", a="b")
    assert client.boto3_session is mock_session
    assert client.botocore_session is botocore_session


def test_create_client_cloudformation():
    mock_session = Mock(spec=["client"])
    botocore_session = object()
    with patch(
        "rpdk.core.boto_helpers._create_sdk_session", autospec=True
    ) as mock_create:
        mock_create.return_value = (mock_session, botocore_session)
        client = create_client("cloudformation", a="b")

    mock_create.assert_called_once_with()
    mock_session.client.assert_called_once_with("cloudformation", a="b")
    assert client.boto3_session is mock_session
    assert client.botocore_session is botocore_session


def test__create_sdk_session_ok():
    patch_botoc = patch("rpdk.core.boto_helpers.BotocoreSession", autospec=True)
    patch_boto3 = patch("rpdk.core.boto_helpers.Boto3Session", autospec=True)

    with patch_botoc as mock_botoc, patch_boto3 as mock_boto3:
        boto3_session, botocore_session = _create_sdk_session()

    assert botocore_session is mock_botoc.return_value
    assert boto3_session is mock_boto3.return_value

    mock_botoc.assert_called_once_with()
    mock_boto3.assert_called_once_with(
        botocore_session=botocore_session,
        # https://github.com/awslabs/aws-cloudformation-rpdk.core.issues/173
        region_name="us-west-2",
    )
    mock_boto3.return_value.get_credentials.assert_called_once_with()


def test__create_sdk_session_no_region():
    patch_botoc = patch("rpdk.core.boto_helpers.BotocoreSession", autospec=True)
    patch_boto3 = patch("rpdk.core.boto_helpers.Boto3Session", autospec=True)

    with patch_botoc as mock_botoc, patch_boto3 as mock_boto3:
        mock_boto3.return_value.region_name = None
        with pytest.raises(SystemExit):
            _create_sdk_session()

    mock_botoc.assert_called_once_with()
    mock_boto3.assert_called_once_with(
        botocore_session=mock_botoc.return_value,
        # https://github.com/awslabs/aws-cloudformation-rpdk.core.issues/173
        region_name="us-west-2",
    )


def test__create_sdk_session_no_creds():
    patch_botoc = patch("rpdk.core.boto_helpers.BotocoreSession", autospec=True)
    patch_boto3 = patch("rpdk.core.boto_helpers.Boto3Session", autospec=True)

    with patch_botoc as mock_botoc, patch_boto3 as mock_boto3:
        mock_boto3.return_value.get_credentials.return_value = None
        with pytest.raises(SystemExit):
            _create_sdk_session()

    mock_botoc.assert_called_once_with()
    mock_boto3.assert_called_once_with(
        botocore_session=mock_botoc.return_value,
        # https://github.com/awslabs/aws-cloudformation-rpdk/issues/173
        region_name="us-west-2",
    )


def test_create_registry_client():
    mock_session = Mock(spec=["client"])
    botocore_session = object()
    with patch(
        "rpdk.core.boto_helpers._create_sdk_session", autospec=True
    ) as mock_create:
        mock_create.return_value = (mock_session, botocore_session)
        client = create_registry_client("cloudformation", a="b")

    mock_create.assert_called_once_with()
    mock_session.client.assert_called_once_with(
        "cloudformation",
        a="b",
        endpoint_url="https://uluru-facade.us-west-2.amazonaws.com",
    )
    assert client.boto3_session is mock_session
    assert client.botocore_session is botocore_session
