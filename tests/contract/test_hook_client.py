# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,protected-access
import json
import logging
import time
from io import StringIO
from unittest import TestCase
from unittest.mock import ANY, patch

import pytest

from rpdk.core.boto_helpers import LOWER_CAMEL_CRED_KEYS
from rpdk.core.contract.hook_client import HookClient
from rpdk.core.contract.interface import (
    HandlerErrorCode,
    HookInvocationPoint,
    HookStatus,
)
from rpdk.core.contract.type_configuration import TypeConfiguration
from rpdk.core.exceptions import InvalidProjectError
from rpdk.core.test import DEFAULT_ENDPOINT, DEFAULT_FUNCTION, DEFAULT_REGION

EMPTY_OVERRIDE = {}
ACCOUNT = "11111111"
LOG = logging.getLogger(__name__)

HOOK_TYPE_NAME = "AWS::UnitTest::Hook"
HOOK_TARGET_TYPE_NAME = "AWS::Example::Resource"
OTHER_HOOK_TARGET_TYPE_NAME = "AWS::Other::Resource"

SCHEMA_ = {
    "typeName": HOOK_TYPE_NAME,
    "description": "Test Hook",
    "typeConfiguration": {
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
            "c": {"type": "number"},
            "d": {"type": "number"},
        },
    },
    "additionalProperties": False,
}

TARGET_SCHEMA = {
    "properties": {
        "a": {"type": "number", "const": 1},
        "b": {"type": "number", "const": 2},
        "c": {"type": "number", "const": 3},
        "d": {"type": "number", "const": 4},
    },
    "readOnlyProperties": ["/properties/b"],
    "createOnlyProperties": ["/properties/c"],
    "primaryIdentifier": ["/properties/c"],
    "writeOnlyProperties": ["/properties/d"],
    "handlers": {"create": {}, "delete": {}, "read": {}},
}

HOOK_CONFIGURATION = '{"CloudFormationConfiguration": {"HookConfiguration": {"Properties": {"key": "value"}}}}'

HOOK_TARGET_INFO = {
    "My::Example::Resource": {
        "TargetName": "My::Example::Resource",
        "TargetType": "RESOURCE",
        "Schema": {
            "typeName": "My::Example::Resource",
            "additionalProperties": False,
            "properties": {
                "Id": {"type": "string"},
                "Tags": {
                    "type": "array",
                    "uniqueItems": False,
                    "items": {"$ref": "#/definitions/Tag"},
                },
            },
            "required": [],
            "definitions": {
                "Tag": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "Value": {"type": "string"},
                        "Key": {"type": "string"},
                    },
                    "required": ["Value", "Key"],
                }
            },
        },
        "ProvisioningType": "FULLY_MUTTABLE",
        "IsCfnRegistrySupportedType": True,
        "SchemaFileAvailable": True,
    }
}


@pytest.fixture
def hook_client():
    endpoint = "https://"
    patch_sesh = patch(
        "rpdk.core.contract.hook_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_account = patch(
        "rpdk.core.contract.hook_client.get_account",
        autospec=True,
        return_value=ACCOUNT,
    )
    with patch_sesh as mock_create_sesh, patch_creds as mock_creds:
        with patch_account as mock_account:
            mock_sesh = mock_create_sesh.return_value
            mock_sesh.region_name = DEFAULT_REGION
            client = HookClient(
                DEFAULT_FUNCTION, endpoint, DEFAULT_REGION, SCHEMA_, EMPTY_OVERRIDE
            )

    mock_sesh.client.assert_called_once_with("lambda", endpoint_url=endpoint)
    mock_creds.assert_called_once_with(mock_sesh, LOWER_CAMEL_CRED_KEYS, None)
    mock_account.assert_called_once_with(mock_sesh, {})
    assert client._function_name == DEFAULT_FUNCTION
    assert client._schema == SCHEMA_
    assert client._configuration_schema == SCHEMA_["typeConfiguration"]
    assert client._overrides == EMPTY_OVERRIDE
    assert client.account == ACCOUNT

    return client


@pytest.fixture
def hook_client_inputs():
    endpoint = "https://"
    patch_sesh = patch(
        "rpdk.core.contract.hook_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_account = patch(
        "rpdk.core.contract.hook_client.get_account",
        autospec=True,
        return_value=ACCOUNT,
    )
    with patch_sesh as mock_create_sesh, patch_creds as mock_creds:
        with patch_account as mock_account:
            mock_sesh = mock_create_sesh.return_value
            mock_sesh.region_name = DEFAULT_REGION
            client = HookClient(
                DEFAULT_FUNCTION,
                endpoint,
                DEFAULT_REGION,
                SCHEMA_,
                EMPTY_OVERRIDE,
                {
                    "CREATE_PRE_PROVISION": {
                        "My::Example::Resource": {"resourceProperties": {"a": 1}}
                    },
                    "UPDATE_PRE_PROVISION": {
                        "My::Example::Resource": {
                            "resourceProperties": {"a": 2},
                            "previousResourceProperties": {"c": 4},
                        }
                    },
                    "INVALID_DELETE_PRE_PROVISION": {
                        "My::Example::Resource": {"resourceProperties": {"b": 2}}
                    },
                    "INVALID": {
                        "My::Example::Resource": {"resourceProperties": {"b": 1}}
                    },
                },
                target_info=HOOK_TARGET_INFO,
            )

    mock_sesh.client.assert_called_once_with("lambda", endpoint_url=endpoint)
    mock_creds.assert_called_once_with(mock_sesh, LOWER_CAMEL_CRED_KEYS, None)
    mock_account.assert_called_once_with(mock_sesh, {})
    assert client._function_name == DEFAULT_FUNCTION
    assert client._schema == SCHEMA_
    assert client._configuration_schema == SCHEMA_["typeConfiguration"]
    assert client._overrides == EMPTY_OVERRIDE
    assert client.account == ACCOUNT

    return client


def test_init_sam_cli_client():
    patch_sesh = patch(
        "rpdk.core.contract.hook_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_account = patch(
        "rpdk.core.contract.hook_client.get_account",
        autospec=True,
        return_value=ACCOUNT,
    )
    with patch_sesh as mock_create_sesh, patch_creds as mock_creds:
        with patch_account as mock_account:
            mock_sesh = mock_create_sesh.return_value
            mock_sesh.region_name = DEFAULT_REGION
            client = HookClient(
                DEFAULT_FUNCTION, DEFAULT_ENDPOINT, DEFAULT_REGION, {}, EMPTY_OVERRIDE
            )

    mock_sesh.client.assert_called_once_with(
        "lambda", endpoint_url=DEFAULT_ENDPOINT, use_ssl=False, verify=False, config=ANY
    )
    mock_creds.assert_called_once_with(mock_sesh, LOWER_CAMEL_CRED_KEYS, None)
    mock_account.assert_called_once_with(mock_sesh, {})
    assert client.account == ACCOUNT


def test_generate_token():
    token = HookClient.generate_token()
    assert isinstance(token, str)
    assert len(token) == 36


def test_setup_target_info():
    hook_target_info = {
        "AWS::Example::Target": {
            "TypeName": "AWS::Example::Target",
            "Schema": TARGET_SCHEMA,
        }
    }

    target_info = HookClient._setup_target_info(hook_target_info)

    assert target_info["AWS::Example::Target"]["readOnlyProperties"] == {
        ("properties", "b")
    }
    assert target_info["AWS::Example::Target"]["createOnlyProperties"] == {
        ("properties", "c")
    }


@pytest.mark.parametrize("hook_type", [None, "Org::Srv::Type"])
@pytest.mark.parametrize("log_group_name", [None, "random_name"])
@pytest.mark.parametrize(
    "log_creds",
    [
        {},
        {
            "AccessKeyId": "access",
            "SecretAccessKey": "secret",
            "SessionToken": "token",
        },
    ],
)
def test_make_request(hook_type, log_group_name, log_creds):
    target_model = object()
    token = object()
    request = HookClient.make_request(
        HOOK_TARGET_TYPE_NAME,
        hook_type,
        ACCOUNT,
        "CREATE_PRE_PROVISION",
        {},
        log_group_name,
        log_creds,
        token,
        target_model,
        "00000001",
        "RESOURCE",
    )

    expected_request = {
        "requestData": {
            "callerCredentials": json.dumps({}),
            "targetName": HOOK_TARGET_TYPE_NAME,
            "targetLogicalId": token,
            "targetModel": target_model,
            "targetType": "RESOURCE",
        },
        "requestContext": {"callbackContext": None},
        "hookTypeName": hook_type,
        "hookTypeVersion": "00000001",
        "clientRequestToken": token,
        "stackId": token,
        "awsAccountId": ACCOUNT,
        "actionInvocationPoint": "CREATE_PRE_PROVISION",
        "hookModel": None,
    }
    if log_group_name and log_creds:
        expected_request["requestData"]["providerCredentials"] = json.dumps(log_creds)
        expected_request["requestData"]["providerLogGroupName"] = log_group_name
    assert request == expected_request


def test_get_handler_target(hook_client):
    targets = [HOOK_TARGET_TYPE_NAME]
    schema = {"handlers": {"preCreate": {"targetNames": targets, "permissions": []}}}
    hook_client._update_schema(schema)

    target_names = hook_client.get_handler_targets(
        HookInvocationPoint.CREATE_PRE_PROVISION
    )
    TestCase().assertCountEqual(target_names, targets)


def test_get_handler_target_no_targets(hook_client):

    schema = {"handlers": {"preCreate": {"permissions": []}}}
    hook_client._update_schema(schema)
    TestCase().assertFalse(
        hook_client.get_handler_targets(HookInvocationPoint.CREATE_PRE_PROVISION)
    )


def test_generate_example(hook_client):
    hook_target_info = {
        "AWS::Example::Target": {
            "TypeName": "AWS::Example::Target",
            "Schema": {
                "properties": {
                    "a": {"type": "number", "const": 1},
                    "b": {"type": "number", "const": 2},
                },
                "readOnlyProperties": ["/properties/b"],
            },
        }
    }
    hook_client._target_info = HookClient._setup_target_info(hook_target_info)
    assert not hook_client._target_info["AWS::Example::Target"].get("SchemaStrategy")

    example = hook_client._generate_target_example("AWS::Example::Target")
    assert example == {"a": 1}
    assert hook_client._target_info["AWS::Example::Target"]["SchemaStrategy"]


def test_generate_update_example(hook_client):
    hook_target_info = {
        "AWS::Example::Target": {
            "TypeName": "AWS::Example::Target",
            "Schema": {
                "properties": {
                    "a": {"type": "number", "const": 1},
                    "b": {"type": "number", "const": 2},
                    "c": {"type": "number", "const": 3},
                },
                "readOnlyProperties": ["/properties/b"],
                "createOnlyProperties": ["/properties/c"],
            },
        }
    }
    hook_client._target_info = HookClient._setup_target_info(hook_target_info)
    hook_client._overrides = {}
    assert not hook_client._target_info["AWS::Example::Target"].get(
        "UpdateSchemaStrategy"
    )

    model = {"b": 2, "a": 4}
    example = hook_client._generate_target_update_example("AWS::Example::Target", model)
    assert example == {"a": 1, "b": 2}
    assert hook_client._target_info["AWS::Example::Target"]["UpdateSchemaStrategy"]


def test_make_payload(hook_client):
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )

    token = "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2f"
    with patch.object(hook_client, "generate_token", return_value=token), patch_creds:
        payload = hook_client._make_payload(
            "CREATE_PRE_PROVISION", HOOK_TARGET_TYPE_NAME, {"foo": "bar"}
        )

    assert payload == {
        "requestData": {
            "callerCredentials": json.dumps({}),
            "targetName": HOOK_TARGET_TYPE_NAME,
            "targetType": "RESOURCE",
            "targetLogicalId": token,
            "targetModel": {"foo": "bar"},
        },
        "requestContext": {"callbackContext": None},
        "hookTypeName": HOOK_TYPE_NAME,
        "hookTypeVersion": "00000001",
        "clientRequestToken": token,
        "stackId": token,
        "awsAccountId": ACCOUNT,
        "actionInvocationPoint": "CREATE_PRE_PROVISION",
        "hookModel": None,
    }


def test_generate_request(hook_client):
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )

    token = "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2f"
    with patch.object(hook_client, "generate_token", return_value=token), patch_creds:
        request = hook_client.generate_request(
            HOOK_TARGET_TYPE_NAME, HookInvocationPoint.DELETE_PRE_PROVISION
        )

    assert request == {
        "requestData": {
            "callerCredentials": json.dumps({}),
            "targetName": HOOK_TARGET_TYPE_NAME,
            "targetLogicalId": token,
            "targetModel": {"resourceProperties": {}},
            "targetType": "RESOURCE",
        },
        "requestContext": {"callbackContext": None},
        "hookTypeName": HOOK_TYPE_NAME,
        "hookTypeVersion": "00000001",
        "clientRequestToken": token,
        "stackId": token,
        "awsAccountId": ACCOUNT,
        "actionInvocationPoint": "DELETE_PRE_PROVISION",
        "hookModel": None,
    }


def test_generate_pre_update_request(hook_client):
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )

    token = "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2f"
    with patch.object(hook_client, "generate_token", return_value=token), patch_creds:
        request = hook_client.generate_request(
            HOOK_TARGET_TYPE_NAME, HookInvocationPoint.UPDATE_PRE_PROVISION
        )

    assert request == {
        "requestData": {
            "callerCredentials": json.dumps({}),
            "targetName": HOOK_TARGET_TYPE_NAME,
            "targetType": "RESOURCE",
            "targetLogicalId": token,
            "targetModel": {
                "resourceProperties": {},
                "previousResourceProperties": {},
            },
        },
        "requestContext": {"callbackContext": None},
        "hookTypeName": HOOK_TYPE_NAME,
        "hookTypeVersion": "00000001",
        "clientRequestToken": token,
        "stackId": token,
        "awsAccountId": ACCOUNT,
        "actionInvocationPoint": "UPDATE_PRE_PROVISION",
        "hookModel": None,
    }


def test_generate_request_example(hook_client):
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    token = "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2f"
    with patch.object(hook_client, "generate_token", return_value=token), patch_creds:
        (
            invocation_point,
            target,
            target_model,
        ) = hook_client.generate_request_example(
            HOOK_TARGET_TYPE_NAME, HookInvocationPoint.CREATE_PRE_PROVISION
        )
    assert invocation_point == HookInvocationPoint.CREATE_PRE_PROVISION
    assert target == HOOK_TARGET_TYPE_NAME
    assert target_model == {"resourceProperties": {}}
    assert not target_model.get("previousResourceProperties")


def test_generate_pre_update_request_example(hook_client):
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    token = "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2f"
    with patch.object(hook_client, "generate_token", return_value=token), patch_creds:
        (
            invocation_point,
            target,
            target_model,
        ) = hook_client.generate_request_example(
            HOOK_TARGET_TYPE_NAME, HookInvocationPoint.UPDATE_PRE_PROVISION
        )
    assert invocation_point == HookInvocationPoint.UPDATE_PRE_PROVISION
    assert target == HOOK_TARGET_TYPE_NAME
    assert target_model == {"resourceProperties": {}, "previousResourceProperties": {}}


def test_generate_request_examples(hook_client):
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    token = "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2f"
    targets = [HOOK_TARGET_TYPE_NAME, OTHER_HOOK_TARGET_TYPE_NAME]
    schema = {
        "typeName": HOOK_TYPE_NAME,
        "handlers": {"preCreate": {"targetNames": targets, "permissions": []}},
    }
    hook_client._update_schema(schema)

    with patch.object(hook_client, "generate_token", return_value=token), patch_creds:
        examples = hook_client.generate_request_examples(
            HookInvocationPoint.CREATE_PRE_PROVISION
        )
    assert len(examples) == len(targets)
    for i in range(len(examples)):
        invoke_point, target, target_model = examples[i]
        assert invoke_point == HookInvocationPoint.CREATE_PRE_PROVISION
        assert target == targets[i]
        assert target_model == {"resourceProperties": {}}
        assert not target_model.get("previousResourceProperties")


def test_generate_invalid_request_examples(hook_client):
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    token = "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2f"
    targets = [HOOK_TARGET_TYPE_NAME, OTHER_HOOK_TARGET_TYPE_NAME]
    schema = {
        "typeName": HOOK_TYPE_NAME,
        "handlers": {"preCreate": {"targetNames": targets, "permissions": []}},
    }
    hook_client._update_schema(schema)

    with patch.object(hook_client, "generate_token", return_value=token), patch_creds:
        examples = hook_client.generate_invalid_request_examples(
            HookInvocationPoint.CREATE_PRE_PROVISION
        )
    assert len(examples) == len(targets)
    for i in range(len(examples)):
        invoke_point, target, target_model = examples[i]
        assert invoke_point == HookInvocationPoint.CREATE_PRE_PROVISION
        assert target == targets[i]
        assert target_model == {"resourceProperties": {}}
        assert not target_model.get("previousResourceProperties")


def test_generate_update_request_examples(hook_client):
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    token = "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2f"
    targets = [HOOK_TARGET_TYPE_NAME, OTHER_HOOK_TARGET_TYPE_NAME]
    schema = {
        "typeName": HOOK_TYPE_NAME,
        "handlers": {"preUpdate": {"targetNames": targets, "permissions": []}},
    }
    hook_client._update_schema(schema)

    with patch.object(hook_client, "generate_token", return_value=token), patch_creds:
        examples = hook_client.generate_request_examples(
            HookInvocationPoint.UPDATE_PRE_PROVISION
        )
    assert len(examples) == len(targets)
    for i in range(len(examples)):
        invoke_point, target, target_model = examples[i]
        assert invoke_point == HookInvocationPoint.UPDATE_PRE_PROVISION
        assert target == targets[i]
        assert target_model == {
            "resourceProperties": {},
            "previousResourceProperties": {},
        }


def test_generate_all_request_examples(hook_client):
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    token = "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2f"
    schema = {
        "typeName": HOOK_TYPE_NAME,
        "handlers": {
            "preCreate": {"targetNames": [HOOK_TARGET_TYPE_NAME], "permissions": []},
            "preUpdate": {
                "targetNames": [OTHER_HOOK_TARGET_TYPE_NAME],
                "permissions": [],
            },
            "preDelete": {
                "targetNames": [HOOK_TARGET_TYPE_NAME, OTHER_HOOK_TARGET_TYPE_NAME],
                "permissions": [],
            },
        },
    }
    hook_client._update_schema(schema)

    with patch.object(hook_client, "generate_token", return_value=token), patch_creds:
        examples = hook_client.generate_all_request_examples()

    pre_create_examples = examples.get(HookInvocationPoint.CREATE_PRE_PROVISION)
    assert pre_create_examples
    assert len(pre_create_examples) == 1
    for example in pre_create_examples:
        invoke_point, target, target_model = example
        assert invoke_point == HookInvocationPoint.CREATE_PRE_PROVISION
        assert target == HOOK_TARGET_TYPE_NAME
        assert target_model == {"resourceProperties": {}}
        assert not target_model.get("previousResourceProperties")

    pre_update_examples = examples.get(HookInvocationPoint.UPDATE_PRE_PROVISION)
    assert pre_update_examples
    assert len(pre_update_examples) == 1
    for example in pre_update_examples:
        invoke_point, target, target_model = example
        assert invoke_point == HookInvocationPoint.UPDATE_PRE_PROVISION
        assert target == OTHER_HOOK_TARGET_TYPE_NAME
        assert target_model == {
            "resourceProperties": {},
            "previousResourceProperties": {},
        }

    pre_delete_examples = examples.get(HookInvocationPoint.DELETE_PRE_PROVISION)
    assert pre_delete_examples
    assert len(pre_delete_examples) == 2
    for example in pre_delete_examples:
        invoke_point, target, target_model = example
        assert invoke_point == HookInvocationPoint.DELETE_PRE_PROVISION
        assert target == HOOK_TARGET_TYPE_NAME or target == OTHER_HOOK_TARGET_TYPE_NAME
        assert target_model == {"resourceProperties": {}}
        assert not target_model.get("previousResourceProperties")


@pytest.mark.parametrize(
    "invoke_point",
    [
        HookInvocationPoint.CREATE_PRE_PROVISION,
        HookInvocationPoint.UPDATE_PRE_PROVISION,
        HookInvocationPoint.DELETE_PRE_PROVISION,
    ],
)
def test_call_sync(hook_client, invoke_point):
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )

    patch_config = patch(
        "rpdk.core.contract.hook_client.TypeConfiguration.get_hook_configuration",
        return_value={},
    )

    mock_client = hook_client._client
    mock_client.invoke.return_value = {"Payload": StringIO('{"hookStatus": "SUCCESS"}')}
    with patch_creds, patch_config:
        status, response = hook_client.call(
            invoke_point, HOOK_TARGET_TYPE_NAME, {"foo": "bar"}
        )

    assert status == HookStatus.SUCCESS
    assert response == {"hookStatus": HookStatus.SUCCESS.value}


def test_call_docker():
    patch_sesh = patch(
        "rpdk.core.contract.hook_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_config = patch(
        "rpdk.core.contract.hook_client.TypeConfiguration.get_hook_configuration",
        return_value={},
    )
    patch_account = patch(
        "rpdk.core.contract.hook_client.get_account",
        autospec=True,
        return_value=ACCOUNT,
    )
    patch_docker = patch("rpdk.core.contract.hook_client.docker", autospec=True)
    with patch_sesh as mock_create_sesh, patch_docker as mock_docker, patch_creds, patch_config:
        with patch_account:
            mock_client = mock_docker.from_env.return_value
            mock_sesh = mock_create_sesh.return_value
            mock_sesh.region_name = DEFAULT_REGION
            hook_client = HookClient(
                DEFAULT_FUNCTION,
                "url",
                DEFAULT_REGION,
                {},
                EMPTY_OVERRIDE,
                docker_image="docker_image",
                executable_entrypoint="entrypoint",
            )
            hook_client._type_name = HOOK_TYPE_NAME
    response_str = (
        "__CFN_HOOK_START_RESPONSE__"
        '{"hookStatus": "SUCCESS"}__CFN_HOOK_END_RESPONSE__'
    )
    mock_client.containers.run.return_value = str.encode(response_str)
    with patch_creds:
        status, response = hook_client.call(
            "CREATE_PRE_PROVISION", HOOK_TARGET_TYPE_NAME, {"foo": "bar"}
        )

    mock_client.containers.run.assert_called_once()
    assert status == HookStatus.SUCCESS
    assert response == {"hookStatus": HookStatus.SUCCESS.value}


def test_call_docker_executable_entrypoint_null():
    TypeConfiguration.TYPE_CONFIGURATION = {}
    patch_sesh = patch(
        "rpdk.core.contract.hook_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_config = patch(
        "rpdk.core.contract.hook_client.TypeConfiguration.get_hook_configuration",
        return_value={},
    )
    patch_account = patch(
        "rpdk.core.contract.hook_client.get_account",
        autospec=True,
        return_value=ACCOUNT,
    )
    patch_docker = patch("rpdk.core.contract.hook_client.docker", autospec=True)
    with patch_sesh as mock_create_sesh, patch_docker, patch_creds, patch_config:
        with patch_account:
            mock_sesh = mock_create_sesh.return_value
            mock_sesh.region_name = DEFAULT_REGION
            hook_client = HookClient(
                DEFAULT_FUNCTION,
                "url",
                DEFAULT_REGION,
                {},
                EMPTY_OVERRIDE,
                docker_image="docker_image",
            )
            hook_client._type_name = HOOK_TYPE_NAME

    try:
        with patch_creds:
            hook_client.call(
                "CREATE_PRE_PROVISION", HOOK_TARGET_TYPE_NAME, {"foo": "bar"}
            )
    except InvalidProjectError:
        pass
    TypeConfiguration.TYPE_CONFIGURATION = None


@pytest.mark.parametrize(
    "invoke_point",
    [
        HookInvocationPoint.CREATE_PRE_PROVISION,
        HookInvocationPoint.UPDATE_PRE_PROVISION,
        HookInvocationPoint.DELETE_PRE_PROVISION,
    ],
)
def test_call_async(hook_client, invoke_point):
    mock_client = hook_client._client

    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )

    patch_config = patch(
        "rpdk.core.contract.hook_client.TypeConfiguration.get_hook_configuration",
        return_value={},
    )

    mock_client.invoke.side_effect = [
        {"Payload": StringIO('{"hookStatus": "IN_PROGRESS"}')},
        {"Payload": StringIO('{"hookStatus": "SUCCESS"}')},
    ]

    with patch_creds, patch_config:
        status, response = hook_client.call(invoke_point, HOOK_TARGET_TYPE_NAME, {})

    assert status == HookStatus.SUCCESS
    assert response == {"hookStatus": HookStatus.SUCCESS.value}


def test_call_and_assert_success(hook_client):
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_config = patch(
        "rpdk.core.contract.hook_client.TypeConfiguration.get_hook_configuration",
        return_value={},
    )
    mock_client = hook_client._client
    mock_client.invoke.return_value = {"Payload": StringIO('{"hookStatus": "SUCCESS"}')}
    with patch_creds, patch_config:
        status, response, error_code = hook_client.call_and_assert(
            HookInvocationPoint.CREATE_PRE_PROVISION,
            HookStatus.SUCCESS,
            HOOK_TARGET_TYPE_NAME,
            {},
        )
    assert status == HookStatus.SUCCESS
    assert response == {"hookStatus": HookStatus.SUCCESS.value}
    assert error_code is None


def test_call_and_assert_failed_invalid_payload(hook_client):
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_config = patch(
        "rpdk.core.contract.hook_client.TypeConfiguration.get_hook_configuration",
        return_value={},
    )
    mock_client = hook_client._client
    mock_client.invoke.return_value = {"Payload": StringIO("invalid json document")}
    with pytest.raises(ValueError), patch_creds, patch_config:
        _status, _response, _error_code = hook_client.call_and_assert(
            HookInvocationPoint.CREATE_PRE_PROVISION,
            HookStatus.SUCCESS,
            HOOK_TARGET_TYPE_NAME,
            {},
        )


def test_call_and_assert_failed(hook_client):
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_config = patch(
        "rpdk.core.contract.hook_client.TypeConfiguration.get_hook_configuration",
        return_value={},
    )
    mock_client = hook_client._client
    mock_client.invoke.return_value = {
        "Payload": StringIO(
            '{"hookStatus": "FAILED","errorCode": "NotFound", "message": "I have failed you"}'
        )
    }
    with patch_creds, patch_config:
        status, response, error_code = hook_client.call_and_assert(
            HookInvocationPoint.DELETE_PRE_PROVISION,
            HookStatus.FAILED,
            HOOK_TARGET_TYPE_NAME,
            {},
        )
    assert status == HookStatus.FAILED
    assert response == {
        "hookStatus": HookStatus.FAILED.value,
        "errorCode": "NotFound",
        "message": "I have failed you",
    }
    assert error_code == HandlerErrorCode.NotFound


def test_call_and_assert_exception_unsupported_status(hook_client):
    mock_client = hook_client._client
    mock_client.invoke.return_value = {
        "Payload": StringIO('{"hookStatus": "FAILED","errorCode": "NotFound"}')
    }
    with pytest.raises(ValueError):
        hook_client.call_and_assert(
            HookInvocationPoint.DELETE_PRE_PROVISION,
            "OtherStatus",
            HOOK_TARGET_TYPE_NAME,
            {},
        )


def test_call_and_assert_exception_assertion_mismatch(hook_client):
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_config = patch(
        "rpdk.core.contract.hook_client.TypeConfiguration.get_hook_configuration",
        return_value={},
    )
    mock_client = hook_client._client
    mock_client.invoke.return_value = {"Payload": StringIO('{"hookStatus": "SUCCESS"}')}
    with pytest.raises(AssertionError), patch_creds, patch_config:
        hook_client.call_and_assert(
            HookInvocationPoint.CREATE_PRE_PROVISION,
            HookStatus.FAILED,
            HOOK_TARGET_TYPE_NAME,
            {},
        )


@pytest.mark.parametrize("status", [HookStatus.SUCCESS, HookStatus.FAILED])
def test_assert_in_progress_wrong_status(status):
    with pytest.raises(AssertionError):
        HookClient.assert_in_progress(status, {})


def test_assert_in_progress_error_code_set():
    with pytest.raises(AssertionError):
        HookClient.assert_in_progress(
            HookStatus.IN_PROGRESS,
            {"errorCode": HandlerErrorCode.AccessDenied.value},
        )


def test_assert_in_progress_result_set():
    with pytest.raises(AssertionError):
        HookClient.assert_in_progress(HookStatus.IN_PROGRESS, {"result": ""})


def test_assert_in_progress_callback_delay_seconds_unset():
    callback_delay_seconds = HookClient.assert_in_progress(
        HookStatus.IN_PROGRESS, {"result": None}
    )
    assert callback_delay_seconds == 0


def test_assert_in_progress_callback_delay_seconds_set():
    callback_delay_seconds = HookClient.assert_in_progress(
        HookStatus.IN_PROGRESS, {"callbackDelaySeconds": 5}
    )
    assert callback_delay_seconds == 5


@pytest.mark.parametrize("status", [HookStatus.IN_PROGRESS, HookStatus.FAILED])
def test_assert_success_wrong_status(status):
    with pytest.raises(AssertionError):
        HookClient.assert_success(status, {})


def test_assert_success_error_code_set():
    with pytest.raises(AssertionError):
        HookClient.assert_success(
            HookStatus.SUCCESS, {"errorCode": HandlerErrorCode.AccessDenied.value}
        )


def test_assert_success_callback_delay_seconds_set():
    with pytest.raises(AssertionError):
        HookClient.assert_success(HookStatus.SUCCESS, {"callbackDelaySeconds": 5})


@pytest.mark.parametrize("status", [HookStatus.IN_PROGRESS, HookStatus.SUCCESS])
def test_assert_failed_wrong_status(status):
    with pytest.raises(AssertionError):
        HookClient.assert_failed(status, {})


def test_assert_failed_error_code_unset():
    with pytest.raises(AssertionError):
        HookClient.assert_failed(HookStatus.FAILED, {})


def test_assert_failed_error_code_invalid():
    with pytest.raises(KeyError):
        HookClient.assert_failed(HookStatus.FAILED, {"errorCode": "XXX"})


def test_assert_failed_callback_delay_seconds_set():
    with pytest.raises(AssertionError):
        HookClient.assert_failed(
            HookStatus.FAILED,
            {
                "errorCode": HandlerErrorCode.AccessDenied.value,
                "callbackDelaySeconds": 5,
            },
        )


def test_assert_failed_returns_error_code():
    error_code = HookClient.assert_failed(
        HookStatus.FAILED,
        {
            "errorCode": HandlerErrorCode.AccessDenied.value,
            "message": "I have failed you",
        },
    )
    assert error_code == HandlerErrorCode.AccessDenied


@pytest.mark.parametrize(
    "invoke_point",
    [
        HookInvocationPoint.CREATE_PRE_PROVISION,
        HookInvocationPoint.UPDATE_PRE_PROVISION,
        HookInvocationPoint.DELETE_PRE_PROVISION,
    ],
)
def test_assert_time(hook_client, invoke_point):
    hook_client.assert_time(time.time() - 59, time.time(), invoke_point)


@pytest.mark.parametrize(
    "invoke_point",
    [
        HookInvocationPoint.CREATE_PRE_PROVISION,
        HookInvocationPoint.UPDATE_PRE_PROVISION,
        HookInvocationPoint.DELETE_PRE_PROVISION,
    ],
)
def test_assert_time_fail(hook_client, invoke_point):
    with pytest.raises(AssertionError):
        hook_client.assert_time(time.time() - 61, time.time(), invoke_point)


@pytest.mark.parametrize(
    "invoke_point",
    [HookInvocationPoint.UPDATE_PRE_PROVISION],
)
def test_is_update_invocation_point_true(invoke_point):
    assert HookClient.is_update_invocation_point(invoke_point)


@pytest.mark.parametrize(
    "invoke_point",
    [
        HookInvocationPoint.CREATE_PRE_PROVISION,
        HookInvocationPoint.DELETE_PRE_PROVISION,
    ],
)
def test_is_update_invocation_point_false(invoke_point):
    assert not HookClient.is_update_invocation_point(invoke_point)


def test_generate_pre_create_target_model_inputs(hook_client_inputs):
    assert hook_client_inputs._generate_target_model(
        "My::Example::Resource", "CREATE_PRE_PROVISION"
    ) == {"resourceProperties": {"a": 1}}


def test_generate_pre_update_target_model_inputs(hook_client_inputs):
    assert hook_client_inputs._generate_target_model(
        "My::Example::Resource", "UPDATE_PRE_PROVISION"
    ) == {"resourceProperties": {"a": 2}, "previousResourceProperties": {"c": 4}}


def test_generate_invalid_pre_create_target_model_inputs(hook_client_inputs):
    assert hook_client_inputs._generate_target_model(
        "My::Example::Resource", "INVALID_CREATE_PRE_PROVISION"
    ) == {"resourceProperties": {"b": 1}}


def test_generate_invalid_pre_delete_target_model_inputs(hook_client_inputs):
    assert hook_client_inputs._generate_target_model(
        "My::Example::Resource", "INVALID_DELETE_PRE_PROVISION"
    ) == {"resourceProperties": {"b": 2}}


def test_generate_invalid_target_model_inputs(hook_client_inputs):
    assert hook_client_inputs._generate_target_model(
        "My::Example::Resource", "INVALID"
    ) == {"resourceProperties": {"b": 1}}
