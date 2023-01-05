from unittest.mock import mock_open, patch

import pytest

from rpdk.core.contract.type_configuration import TypeConfiguration
from rpdk.core.exceptions import InvalidProjectError

TYPE_CONFIGURATION_TEST_SETTING = (
    '{"Credentials" :{"ApiKey": "123", "ApplicationKey": "123"}}'
)

TYPE_CONFIGURATION_INVALID = '{"Credentials" :{"ApiKey": "123", xxxx}}'

HOOK_CONFIGURATION_TEST_SETTING = '{"CloudFormationConfiguration": {"HookConfiguration": {"Properties": {"Credentials" :{"ApiKey": "123", "ApplicationKey": "123"}}}}}'

HOOK_CONFIGURATION_INVALID = '{"CloudFormationConfiguration": {"TypeConfiguration": {"Properties": {"Credentials" :{"ApiKey": "123", "ApplicationKey": "123"}}}}}'


def setup_function():
    # Resetting before each test
    TypeConfiguration.TYPE_CONFIGURATION = None


def teardown_function():
    # Rest after to clean TypeConfiguration before the next test
    TypeConfiguration.TYPE_CONFIGURATION = None


def test_get_type_configuration_with_not_exist_file():
    with patch("builtins.open", mock_open()) as f:
        f.side_effect = FileNotFoundError()
        assert TypeConfiguration.get_type_configuration() is None


@patch("builtins.open", mock_open(read_data=TYPE_CONFIGURATION_TEST_SETTING))
def test_get_type_configuration():
    type_configuration = TypeConfiguration.get_type_configuration()
    assert type_configuration["Credentials"]["ApiKey"] == "123"
    assert type_configuration["Credentials"]["ApplicationKey"] == "123"

    # get type config again, should be the same config
    type_configuration = TypeConfiguration.get_type_configuration()
    assert type_configuration["Credentials"]["ApiKey"] == "123"
    assert type_configuration["Credentials"]["ApplicationKey"] == "123"


@patch("builtins.open", mock_open(read_data=TYPE_CONFIGURATION_INVALID))
def test_get_type_configuration_with_invalid_json():
    try:
        TypeConfiguration.get_type_configuration()
    except InvalidProjectError:
        pass


@patch("builtins.open", mock_open(read_data=HOOK_CONFIGURATION_TEST_SETTING))
def test_get_hook_configuration():
    hook_configuration = TypeConfiguration.get_hook_configuration()
    assert hook_configuration["Credentials"]["ApiKey"] == "123"
    assert hook_configuration["Credentials"]["ApplicationKey"] == "123"

    # get type config again, should be the same config
    hook_configuration = TypeConfiguration.get_hook_configuration()
    assert hook_configuration["Credentials"]["ApiKey"] == "123"
    assert hook_configuration["Credentials"]["ApplicationKey"] == "123"


@patch("builtins.open", mock_open(read_data=HOOK_CONFIGURATION_INVALID))
def test_get_hook_configuration_with_invalid_json():
    with pytest.raises(InvalidProjectError) as execinfo:
        TypeConfiguration.get_hook_configuration()

    assert "Hook configuration is invalid" in str(execinfo.value)


def test_get_hook_configuration_with_not_exist_file():
    with patch("builtins.open", mock_open()) as f:
        f.side_effect = FileNotFoundError()
        assert TypeConfiguration.get_hook_configuration() is None
