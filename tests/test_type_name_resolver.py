# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,no-else-return,protected-access

from unittest.mock import Mock, call, patch

import pytest
from botocore.exceptions import ClientError

from rpdk.core.exceptions import DownstreamError, InvalidTypeSchemaError
from rpdk.core.type_name_resolver import TypeNameResolver


@pytest.fixture()
def resolver():
    return TypeNameResolver(Mock())


def list_types_request(visibility, filters=None):
    req = {
        "Type": "RESOURCE",
        "Visibility": visibility,
        "DeprecatedStatus": "LIVE",
        "MaxResults": 100,
        "PaginationConfig": {"PageSize": 100},
    }
    if filters:
        req["Filters"] = filters

    return req


def list_types_result(type_names):
    return {
        "TypeSummaries": [
            {
                "Type": "RESOURCE",
                "TypeName": type_name,
                "TypeArn": (
                    f'arn:aws:cloudformation:us-east-1:123456789012:type/resource/{type_name.replace("::", "-")}'  # noqa: E231
                ),
            }
            for type_name in type_names
        ]
    }


def test_resolve_type_names(resolver):
    def list_type_return(**kwargs):
        if kwargs["Visibility"] == "PUBLIC":
            return [list_types_result(["AWS::S3::Bucket", "AWS::Logs::LogGroup"])]
        else:
            return [list_types_result(["MyCompany::Testing::Hook"])]

    mock_cfn_client = Mock(spec=["get_paginator"])
    mock_paginator = Mock(spec=["paginate"])
    mock_cfn_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.side_effect = list_type_return

    resolver.cfn_client = mock_cfn_client

    assert [
        "AWS::Logs::LogGroup",
        "MyCompany::Testing::Hook",
    ] == resolver.resolve_type_names(["AWS::*::LogGroup", "MyCompany::Testing::Hook"])
    mock_paginator.paginate.assert_has_calls(
        calls=[
            call(**list_types_request("PUBLIC")),
            call(**list_types_request("PRIVATE")),
        ],
        any_order=True,
    )


def test_resolve_type_names_multiple_wildcards(resolver):
    def list_type_return(**kwargs):
        if kwargs["Visibility"] == "PUBLIC":
            return [list_types_result(["AWS::S3::Bucket", "AWS::Logs::LogGroup"])]
        else:
            return [list_types_result(["MyCompany::Testing::Hook"])]

    mock_cfn_client = Mock(spec=["get_paginator"])
    mock_paginator = Mock(spec=["paginate"])
    mock_cfn_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.side_effect = list_type_return

    resolver.cfn_client = mock_cfn_client

    assert [
        "AWS::Logs::LogGroup",
        "AWS::S3::Bucket",
        "MyCompany::Testing::Hook",
    ] == resolver.resolve_type_names(["AWS::*", "MyCompany::Testing::Hook"])
    mock_paginator.paginate.assert_has_calls(
        calls=[
            call(**list_types_request("PUBLIC")),
            call(**list_types_request("PRIVATE")),
        ],
        any_order=True,
    )


def test_resolve_type_names_common_prefix(resolver):
    def list_type_return(**kwargs):
        if kwargs["Visibility"] == "PUBLIC":
            return [
                list_types_result(
                    [
                        "AWS::S3::Bucket",
                        "AWS::Logs::LogGroup",
                        "AWS::Logs::LogStream",
                        "AWS::SQS::Queue",
                    ]
                )
            ]
        else:
            return []

    mock_cfn_client = Mock(spec=["get_paginator"])
    mock_paginator = Mock(spec=["paginate"])
    mock_cfn_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.side_effect = list_type_return

    resolver.cfn_client = mock_cfn_client

    assert [
        "AWS::Logs::LogGroup",
        "AWS::Logs::LogStream",
        "AWS::S3::Bucket",
    ] == resolver.resolve_type_names(["AWS::*::Log*", "AWS::S3::Bucket"])
    mock_paginator.paginate.assert_has_calls(
        calls=[
            call(**list_types_request("PUBLIC", filters={"TypeNamePrefix": "AWS::"})),
            call(**list_types_request("PRIVATE", filters={"TypeNamePrefix": "AWS::"})),
        ],
        any_order=True,
    )


def test_resolve_type_names_glob_wildcard(resolver):
    def list_type_return(**kwargs):
        if kwargs["Visibility"] == "PUBLIC":
            return [list_types_result(["AWS::S3::Bucket", "AWS::Logs::LogGroup"])]
        else:
            return [list_types_result(["MyCompany::Testing::Hook"])]

    mock_cfn_client = Mock(spec=["get_paginator"])
    mock_paginator = Mock(spec=["paginate"])
    mock_cfn_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.side_effect = list_type_return

    resolver.cfn_client = mock_cfn_client

    assert [
        "AWS::Logs::LogGroup",
        "AWS::S3::Bucket",
        "MyCompany::Testing::Hook",
    ] == resolver.resolve_type_names(["*"])
    mock_paginator.paginate.assert_has_calls(
        calls=[
            call(**list_types_request("PUBLIC")),
            call(**list_types_request("PRIVATE")),
        ],
        any_order=True,
    )


def test_resolve_type_names_no_wildcards(resolver):
    mock_cfn_client = Mock(spec=["get_paginator"])
    mock_paginator = Mock(spec=["paginate"])
    mock_cfn_client.get_paginator.return_value = mock_paginator

    # loader.cfn_client = mock_cfn_client

    assert [
        "AWS::Logs::LogGroup",
        "MyCompany::Testing::Hook",
    ] == resolver.resolve_type_names(
        ["AWS::Logs::LogGroup", "MyCompany::Testing::Hook"]
    )
    resolver.cfn_client.get_paginator.assert_not_called()


def test_resolve_type_names_client_error(resolver):
    e = ClientError({"Error": {"Code": "", "Message": "Invalid request"}}, "list_types")

    mock_cfn_client = Mock(spec=["get_paginator"])
    mock_paginator = Mock(spec=["paginate"])
    mock_cfn_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.side_effect = e

    resolver.cfn_client = mock_cfn_client

    with pytest.raises(DownstreamError) as excinfo:
        resolver.resolve_type_names(["AWS::*::LogGroup", "MyCompany::Testing::Hook"])

    assert excinfo.value.__cause__ is e
    mock_paginator.paginate.assert_called_once()


def test_resolve_type_names_locally(resolver):
    local_info = {
        "AWS::S3::Bucket": {"ProvisioningType": "FULLY_MUTABLE"},
        "AWS::Logs::LogGroup": {"ProvisioningType": "IMMUTABLE"},
        "AWS::Logs::LogStream": {"ProvisioningType": "NON_PROVISIONAL"},
        "MyCompany::Test::Hook": {},
    }

    patch_list_hooks = patch.object(
        resolver, "list_applicable_types", wraps=resolver.list_applicable_types
    )

    with patch_list_hooks as mock_list_hooks:
        assert [
            "AWS::Logs::LogGroup",
            "AWS::Logs::LogStream",
            "AWS::S3::Bucket",
        ] == resolver.resolve_type_names_locally(
            ["AWS::*::Log*", "AWS::S3::Bucket"], local_info
        )

    mock_list_hooks.assert_not_called()


def test_resolve_type_names_locally_no_local_info(resolver):
    with pytest.raises(InvalidTypeSchemaError) as excinfo:
        resolver.resolve_type_names_locally(["AWS::*::Log*", "AWS::S3::Bucket"], None)

    assert "Type info must be provided for local resolving" in str(excinfo.value)


@pytest.mark.parametrize(
    "type_names,expected",
    [
        ([], None),
        (["AWS::Test::Resource"], "AWS::Test::Resource"),
        (["AWS::Test::Resource", "MyCompany::Test::Resource"], None),
        (["AWS::S3::Bucket", "AWS::SQS::Queue"], "AWS::S"),
        (["AWS::S3::*Bucket"], "AWS::S3::"),
        (["AWS::S?::Bucket"], "AWS::S"),
        (["AWS::S?::*Bucket"], "AWS::S"),
        (["AWS::*::Log*"], "AWS::"),
        (["A*::S?::Bucket*"], None),
        (["*::S?::Bucket*"], ""),
        (["AWS::S?::BucketPolicy", "AWS::S3::Bucket"], "AWS::S"),
        (["AWS::S*::Queue", "AWS::DynamoDB::*"], "AWS::"),
        (["AwsCommunity::S3::BucketVersioningEnabled", "AWS::*"], None),
        (["AWSSamples::*", f'AW{"S" * 64}*', "AWS::S3::Bucket"], "AWS"),
        ([f'AW{"S" * 64}*'], None),
    ],
)
def test_create_list_types_request(type_names, expected):
    req = TypeNameResolver._create_list_types_request(type_names)
    if not expected:
        assert not req
    else:
        assert req == {"Filters": {"TypeNamePrefix": expected}}
