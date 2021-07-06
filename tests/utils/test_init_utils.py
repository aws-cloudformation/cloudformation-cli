from unittest.mock import Mock, patch

import pytest

from rpdk.core.exceptions import WizardValidationError
from rpdk.core.utils.init_utils import (
    init_artifact_type,
    input_with_validation,
    validate_artifact_type,
    validate_yes,
)
from tests.test_init import ERROR, PROMPT


def test_input_artifact_type():
    artifact_type = "MODULE"
    patch_input = patch("rpdk.core.utils.init_utils.input", return_value=artifact_type)
    with patch_input as mock_input:
        assert init_artifact_type() == artifact_type
    mock_input.assert_called_once()


def test_input_modules_bad_arg_but_valid_input():
    artifact_type = "MODULE"
    patch_input = patch("rpdk.core.utils.init_utils.input", return_value=artifact_type)
    mock_args = Mock()
    mock_args.artifact_type.return_value = "Not a valid type"
    with patch_input as mock_input:
        assert init_artifact_type(mock_args) == artifact_type
    mock_input.assert_called_once()


def test_input_with_validation_valid_first_try(capsys):
    sentinel1 = object()
    sentinel2 = object()

    validator = Mock(return_value=sentinel1)
    with patch(
        "rpdk.core.utils.init_utils.input", return_value=sentinel2
    ) as mock_input:
        ret = input_with_validation(PROMPT, validator)

    mock_input.assert_called_once_with()
    validator.assert_called_once_with(sentinel2)
    assert ret is sentinel1

    out, err = capsys.readouterr()
    assert not err
    assert PROMPT in out


def test_input_with_validation_valid_second_try(capsys):
    def mock_validator(value):
        if value == ERROR:
            raise WizardValidationError(ERROR)
        return value

    sentinel = object()

    with patch(
        "rpdk.core.utils.init_utils.input", side_effect=(ERROR, sentinel)
    ) as mock_input:
        ret = input_with_validation(PROMPT, mock_validator)

    assert mock_input.call_count == 2
    assert ret is sentinel

    out, err = capsys.readouterr()
    assert not err
    assert ERROR in out


def test_validate_artifact_type_valid():
    assert validate_artifact_type("m") == "MODULE"
    assert validate_artifact_type("module") == "MODULE"
    assert validate_artifact_type("r") == "RESOURCE"
    assert validate_artifact_type("resource") == "RESOURCE"


def test_validate_artifact_type_invalid():
    with pytest.raises(WizardValidationError):
        validate_artifact_type("invalid_type")


@pytest.mark.parametrize("value", ("y", "yes", "Y", "YES", "yEs", "YeS"))
def test_validate_yes_yes(value):
    assert validate_yes(value)


@pytest.mark.parametrize("value", ("n", "N", "no", "NO", "yesn't"))
def test_validate_yes_no(value):
    assert not validate_yes(value)
