from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest

from rpdk.core.exceptions import WizardValidationError
from rpdk.core.module import init_module
from rpdk.core.module.init_module import validate_type_name


def test_validate_type_name_invalid():
    with pytest.raises(WizardValidationError):
        validate_type_name("AWS-Color-Red")


def test_validate_type_name_valid():
    assert validate_type_name("AWS::Color::Red::MODULE") == "AWS::Color::Red::MODULE"


def test_init_module_falls_back_to_user_input_if_arg_invalid():
    patch_validate = patch.object(
        init_module, "validate_type_name", side_effect=WizardValidationError
    )
    patch_input = patch.object(
        init_module, "input_typename", return_value="Module::Mc::Modulson::MODULE"
    )
    mock_project = MagicMock()
    with TemporaryDirectory() as temporary_directory:
        mock_project.root = temporary_directory
        mock_args = MagicMock()
        mock_args.type_name.return_value = "Not a valid type"
        with patch_validate, patch_input:
            init_module.init_module(mock_args, mock_project)
        mock_project.init_module.assert_called_once_with("Module::Mc::Modulson::MODULE")
