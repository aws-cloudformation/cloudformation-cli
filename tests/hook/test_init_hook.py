from unittest.mock import patch

import pytest

from rpdk.core.exceptions import WizardAbortError, WizardValidationError
from rpdk.core.hook.init_hook import (
    ValidatePluginChoice,
    input_language,
    input_typename,
    validate_type_name,
)
from tests.test_init import PROMPT


def test_input_typename():
    type_name = "AWS::CFN::HOOK"
    patch_input = patch(
        "rpdk.core.hook.init_hook.input_with_validation", return_value=type_name
    )
    with patch_input as mock_input:
        assert input_typename() == type_name
    mock_input.assert_called_once()


def test_input_language_no_plugins():
    validator = ValidatePluginChoice([])
    with patch("rpdk.core.hook.init_hook.validate_plugin_choice", validator):
        with pytest.raises(WizardAbortError):
            input_language()


def test_input_language_one_plugin():
    validator = ValidatePluginChoice([PROMPT])
    with patch("rpdk.core.hook.init_hook.validate_plugin_choice", validator):
        assert input_language() == PROMPT


def test_input_language_several_plugins():
    validator = ValidatePluginChoice(["1", PROMPT, "2"])
    patch_validator = patch(
        "rpdk.core.hook.init_hook.validate_plugin_choice", validator
    )
    patch_input = patch("rpdk.core.utils.init_utils.input", return_value="2")
    with patch_validator, patch_input as mock_input:
        assert input_language() == PROMPT

    mock_input.assert_called_once()


def test_validate_plugin_choice_not_an_int():
    validator = ValidatePluginChoice(["test"])
    with pytest.raises(WizardValidationError) as excinfo:
        validator("a")
    assert "integer" in str(excinfo.value)


def test_validate_plugin_choice_less_than_zero():
    validator = ValidatePluginChoice(["test"])
    with pytest.raises(WizardValidationError) as excinfo:
        validator("-1")
    assert "select" in str(excinfo.value)


def test_validate_plugin_choice_greater_than_choice():
    choices = range(3)
    validator = ValidatePluginChoice(choices)
    with pytest.raises(WizardValidationError) as excinfo:
        validator(str(len(choices) + 1))  # index is 1 based for input
    assert "select" in str(excinfo.value)


def test_validate_plugin_choice_valid():
    choices = ["1", PROMPT, "2"]
    validator = ValidatePluginChoice(choices)
    assert validator("2") == PROMPT


def test_validate_type_name_invalid():
    with pytest.raises(WizardValidationError):
        validate_type_name("AWS-CFN-HOOK")


def test_validate_type_name_valid():
    assert validate_type_name("AWS::CFN::HOOK") == "AWS::CFN::HOOK"
