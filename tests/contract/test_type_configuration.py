from unittest.mock import mock_open, patch

from rpdk.core.contract.type_configuration import TypeConfiguration
from rpdk.core.exceptions import InvalidProjectError

TYPE_CONFIGURATION_TEST_SETTING = (
    '{"Credentials" :{"ApiKey": "123", "ApplicationKey": "123"}}'
)

TYPE_CONFIGURATION_INVALID = '{"Credentials" :{"ApiKey": "123", xxxx}}'


def test_get_type_configuration_with_not_exist_file():
    with patch("builtins.open", mock_open()) as f:
        f.side_effect = FileNotFoundError()
        try:
            TypeConfiguration.get_type_configuration()
        except FileNotFoundError:
            pass


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
