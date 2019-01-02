from unittest.mock import ANY, Mock, PropertyMock, patch

import pytest

from rpdk.init import (
    AbortError,
    ValidatePluginChoice,
    ValidationError,
    check_for_existing_project,
    ignore_abort,
    init,
    input_language,
    input_typename,
    input_with_validation,
    validate_type_name,
    validate_yes,
)
from rpdk.project import Project

PROMPT = "MECVGD"
ERROR = "TUJFEL"


def test_init_method():
    type_name = object()
    language = object()

    args = Mock(spec_set=["force"])
    args.force = False

    mock_project = Mock(spec=Project)
    mock_project.load_settings.side_effect = FileNotFoundError
    mock_project.settings_path = ""

    patch_project = patch("rpdk.init.Project", return_value=mock_project)
    patch_tn = patch("rpdk.init.input_typename", return_value=type_name)
    patch_l = patch("rpdk.init.input_language", return_value=language)

    with patch_project, patch_tn as mock_tn, patch_l as mock_l:
        init(args)

    mock_tn.assert_called_once_with()
    mock_l.assert_called_once_with()

    mock_project.load_settings.assert_called_once_with()
    mock_project.init.assert_called_once_with(type_name, language)
    mock_project.generate.assert_called_once_with()


def test_input_with_validation_valid_first_try():
    sentinel1 = object()
    sentinel2 = object()

    validator = Mock(return_value=sentinel1)
    with patch("rpdk.init.input", return_value=sentinel2) as mock_input:
        ret = input_with_validation(PROMPT, validator)

    mock_input.assert_called_once_with(PROMPT)
    validator.assert_called_once_with(sentinel2)
    assert ret is sentinel1


def test_input_with_validation_valid_second_try(capsys):
    def mock_validator(value):
        if value == ERROR:
            raise ValidationError(ERROR)
        return value

    sentinel = object()

    with patch("rpdk.init.input", side_effect=(ERROR, sentinel)) as mock_input:
        ret = input_with_validation(PROMPT, mock_validator)

    assert mock_input.call_count == 2
    assert ret is sentinel

    out, err = capsys.readouterr()
    assert not err
    assert ERROR in out


def test_validate_type_name_valid():
    assert validate_type_name("AWS::Color::Red") == "AWS::Color::Red"


def test_validate_type_name_invalid():
    with pytest.raises(ValidationError):
        validate_type_name("AWS-Color-Red")


@pytest.mark.parametrize("value", ("y", "yes", "Y", "YES", "yEs", "YeS"))
def test_validate_yes_yes(value):
    assert validate_yes(value)


@pytest.mark.parametrize("value", ("n", "N", "no", "NO", "yesn't"))
def test_validate_yes_no(value):
    assert not validate_yes(value)


def test_validate_plugin_choice_not_an_int():
    validator = ValidatePluginChoice(["test"])
    with pytest.raises(ValidationError) as excinfo:
        validator("a")
    assert "integer" in str(excinfo.value)


def test_validate_plugin_choice_less_than_zero():
    validator = ValidatePluginChoice(["test"])
    with pytest.raises(ValidationError) as excinfo:
        validator("-1")
    assert "select" in str(excinfo.value)


def test_validate_plugin_choice_greater_than_choice():
    choices = range(3)
    validator = ValidatePluginChoice(choices)
    with pytest.raises(ValidationError) as excinfo:
        validator(str(len(choices) + 1))  # index is 1 based for input
    assert "select" in str(excinfo.value)


def test_validate_plugin_choice_valid():
    choices = ["1", PROMPT, "2"]
    validator = ValidatePluginChoice(choices)
    assert validator("2") == PROMPT


def test_check_for_existing_project_good_path():
    project = Mock(spec=Project)
    project.load_settings.side_effect = FileNotFoundError
    type(project).overwrite = mock_overwrite = PropertyMock()

    check_for_existing_project(project)

    project.load_settings.assert_called_once_with()
    mock_overwrite.assert_not_called()


def test_check_for_existing_project_bad_path_overwrite():
    project = Mock(spec=Project)
    project.overwrite = True
    project.settings_path = ""  # not sure why this doesn't get specced?

    with patch("rpdk.init.input_with_validation", autospec=True) as mock_input:
        check_for_existing_project(project)

    mock_input.assert_not_called()


def test_check_for_existing_project_bad_path_ask_yes():
    project = Mock(spec=Project)
    project.overwrite = False
    project.settings_path = ""

    patch_input = patch(
        "rpdk.init.input_with_validation", autospec=True, return_value=True
    )
    with patch_input as mock_input:
        check_for_existing_project(project)

    mock_input.assert_called_once_with(ANY, validate_yes)
    assert project.overwrite


def test_check_for_existing_project_bad_path_ask_no():
    project = Mock(spec=Project)
    project.overwrite = False
    project.settings_path = ""

    patch_input = patch(
        "rpdk.init.input_with_validation", autospec=True, return_value=False
    )
    with patch_input as mock_input:
        with pytest.raises(AbortError):
            check_for_existing_project(project)

    mock_input.assert_called_once_with(ANY, validate_yes)
    assert not project.overwrite


def test_ignore_abort_ok():
    sentinel = object()
    function = Mock()
    wrapped = ignore_abort(function)

    wrapped(sentinel)
    function.assert_called_once_with(sentinel)


def test_ignore_abort_keyboard_interrupt():
    sentinel = object()
    function = Mock(side_effect=KeyboardInterrupt)
    wrapped = ignore_abort(function)

    with pytest.raises(SystemExit):
        wrapped(sentinel)
    function.assert_called_once_with(sentinel)


def test_ignore_abort_abort():
    sentinel = object()
    function = Mock(side_effect=AbortError)
    wrapped = ignore_abort(function)

    with pytest.raises(SystemExit):
        wrapped(sentinel)
    function.assert_called_once_with(sentinel)


def test_input_typename():
    type_name = "AWS::Color::Red"
    patch_input = patch("rpdk.init.input", return_value=type_name)
    with patch_input as mock_input:
        assert input_typename() == type_name
    mock_input.assert_called_once()


def test_input_language_no_plugins():
    validator = ValidatePluginChoice([])
    with patch("rpdk.init.validate_plugin_choice", validator):
        with pytest.raises(AbortError):
            input_language()


def test_input_language_one_plugin():
    validator = ValidatePluginChoice([PROMPT])
    with patch("rpdk.init.validate_plugin_choice", validator):
        assert input_language() == PROMPT


def test_input_language_several_plugins():
    validator = ValidatePluginChoice(["1", PROMPT, "2"])
    patch_validator = patch("rpdk.init.validate_plugin_choice", validator)
    patch_input = patch("rpdk.init.input", return_value="2")
    with patch_validator, patch_input as mock_input:
        assert input_language() == PROMPT

    mock_input.assert_called_once()
