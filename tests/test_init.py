from pathlib import Path
from unittest.mock import ANY, Mock, PropertyMock, patch

import pkg_resources
import pytest

from rpdk.core.exceptions import WizardAbortError, WizardValidationError
from rpdk.core.init import (
    ValidatePluginChoice,
    check_for_existing_project,
    ignore_abort,
    init,
    input_language,
    input_typename,
    input_with_validation,
    validate_type_name,
    validate_yes,
)
from rpdk.core.project import Project

PROMPT = "MECVGD"
ERROR = "TUJFEL"


def add_dummy_language_plugin():
    distribution = pkg_resources.Distribution(__file__)
    entry_point = pkg_resources.EntryPoint.parse(
        "dummy = rpdk.dummy:DummyLanguagePlugin", dist=distribution
    )
    distribution._ep_map = {  # pylint: disable=protected-access
        "rpdk.v1.languages": {"dummy": entry_point}
    }
    pkg_resources.working_set.add(distribution)


def get_mock_project():
    mock_project = Mock(spec=Project)
    mock_project.load_settings.side_effect = FileNotFoundError
    mock_project.settings_path = ""
    mock_project.root = Path(".")

    patch_project = patch("rpdk.core.init.Project", return_value=mock_project)

    return (mock_project, patch_project)


def get_args(interactive=False, language=True, type_name=True):
    args = Mock(spec_set=["force", "language", "type_name", "use_docker", "namespace"])
    args.force = False
    args.language = (
        None if interactive else ("dummy" if language else "invalid_language")
    )
    args.type_name = (
        None if interactive else ("Test::Test::Test" if type_name else "Test")
    )
    args.use_docker = True
    args.namespace = "tested.by.the.plugin"

    return args


def test_init_method_interactive():
    type_name = object()
    language = object()

    args = get_args(interactive=True)
    mock_project, patch_project = get_mock_project()

    patch_tn = patch("rpdk.core.init.input_typename", return_value=type_name)
    patch_l = patch("rpdk.core.init.input_language", return_value=language)

    with patch_project, patch_tn as mock_tn, patch_l as mock_l:
        init(args)

    mock_tn.assert_called_once_with()
    mock_l.assert_called_once_with()

    mock_project.load_settings.assert_called_once_with()
    mock_project.init.assert_called_once_with(
        type_name,
        language,
        {"use_docker": args.use_docker, "namespace": args.namespace},
    )
    mock_project.generate.assert_called_once_with()


def test_init_method_noninteractive():
    add_dummy_language_plugin()

    args = get_args()
    mock_project, patch_project = get_mock_project()

    patch_tn = patch("rpdk.core.init.input_typename")
    patch_l = patch("rpdk.core.init.input_language")

    with patch_project, patch_tn as mock_tn, patch_l as mock_l:
        init(args)

    mock_tn.assert_not_called()
    mock_l.assert_not_called()

    mock_project.load_settings.assert_called_once_with()
    mock_project.init.assert_called_once_with(
        args.type_name,
        args.language,
        {"use_docker": args.use_docker, "namespace": args.namespace},
    )
    mock_project.generate.assert_called_once_with()


def test_init_method_noninteractive_invalid_type_name():
    add_dummy_language_plugin()
    type_name = object()

    args = get_args(type_name=False)
    mock_project, patch_project = get_mock_project()

    patch_tn = patch("rpdk.core.init.input_typename", return_value=type_name)
    patch_l = patch("rpdk.core.init.input_language")

    with patch_project, patch_tn as mock_tn, patch_l as mock_l:
        init(args)

    mock_tn.assert_called_once_with()
    mock_l.assert_not_called()

    mock_project.load_settings.assert_called_once_with()
    mock_project.init.assert_called_once_with(
        type_name,
        args.language,
        {"use_docker": args.use_docker, "namespace": args.namespace},
    )
    mock_project.generate.assert_called_once_with()


def test_init_method_noninteractive_invalid_language():
    language = object()

    args = get_args(language=False)
    mock_project, patch_project = get_mock_project()

    patch_tn = patch("rpdk.core.init.input_typename")
    patch_l = patch("rpdk.core.init.input_language", return_value=language)

    with patch_project, patch_tn as mock_tn, patch_l as mock_l:
        init(args)

    mock_tn.assert_not_called()
    mock_l.assert_called_once_with()

    mock_project.load_settings.assert_called_once_with()
    mock_project.init.assert_called_once_with(
        args.type_name,
        language,
        {"use_docker": args.use_docker, "namespace": args.namespace},
    )
    mock_project.generate.assert_called_once_with()


def test_input_with_validation_valid_first_try(capsys):
    sentinel1 = object()
    sentinel2 = object()

    validator = Mock(return_value=sentinel1)
    with patch("rpdk.core.init.input", return_value=sentinel2) as mock_input:
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

    with patch("rpdk.core.init.input", side_effect=(ERROR, sentinel)) as mock_input:
        ret = input_with_validation(PROMPT, mock_validator)

    assert mock_input.call_count == 2
    assert ret is sentinel

    out, err = capsys.readouterr()
    assert not err
    assert ERROR in out


def test_validate_type_name_valid():
    assert validate_type_name("AWS::Color::Red") == "AWS::Color::Red"


def test_validate_type_name_invalid():
    with pytest.raises(WizardValidationError):
        validate_type_name("AWS-Color-Red")


@pytest.mark.parametrize("value", ("y", "yes", "Y", "YES", "yEs", "YeS"))
def test_validate_yes_yes(value):
    assert validate_yes(value)


@pytest.mark.parametrize("value", ("n", "N", "no", "NO", "yesn't"))
def test_validate_yes_no(value):
    assert not validate_yes(value)


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


def test_check_for_existing_project_good_path():
    project = Mock(spec=Project)
    project.load_settings.side_effect = FileNotFoundError
    type(project).overwrite_enabled = mock_overwrite = PropertyMock()

    check_for_existing_project(project)

    project.load_settings.assert_called_once_with()
    mock_overwrite.assert_not_called()


def test_check_for_existing_project_bad_path_overwrite():
    project = Mock(spec=Project)
    project.overwrite_enabled = True
    project.settings_path = ""  # not sure why this doesn't get specced?
    project.type_name = ""

    with patch("rpdk.core.init.input_with_validation", autospec=True) as mock_input:
        check_for_existing_project(project)

    mock_input.assert_not_called()


def test_check_for_existing_project_bad_path_ask_yes():
    project = Mock(spec=Project)
    project.overwrite_enabled = False
    project.settings_path = ""
    project.type_name = ""

    patch_input = patch(
        "rpdk.core.init.input_with_validation", autospec=True, return_value=True
    )
    with patch_input as mock_input:
        check_for_existing_project(project)

    mock_input.assert_called_once_with(ANY, validate_yes, ANY)
    assert project.overwrite_enabled


def test_check_for_existing_project_bad_path_ask_no():
    project = Mock(spec=Project)
    project.overwrite_enabled = False
    project.settings_path = ""
    project.type_name = ""

    patch_input = patch(
        "rpdk.core.init.input_with_validation", autospec=True, return_value=False
    )
    with patch_input as mock_input:
        with pytest.raises(WizardAbortError):
            check_for_existing_project(project)

    mock_input.assert_called_once_with(ANY, validate_yes, ANY)
    assert not project.overwrite_enabled


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
    function = Mock(side_effect=WizardAbortError)
    wrapped = ignore_abort(function)

    with pytest.raises(SystemExit):
        wrapped(sentinel)
    function.assert_called_once_with(sentinel)


def test_input_typename():
    type_name = "AWS::Color::Red"
    patch_input = patch("rpdk.core.init.input", return_value=type_name)
    with patch_input as mock_input:
        assert input_typename() == type_name
    mock_input.assert_called_once()


def test_input_language_no_plugins():
    validator = ValidatePluginChoice([])
    with patch("rpdk.core.init.validate_plugin_choice", validator):
        with pytest.raises(WizardAbortError):
            input_language()


def test_input_language_one_plugin():
    validator = ValidatePluginChoice([PROMPT])
    with patch("rpdk.core.init.validate_plugin_choice", validator):
        assert input_language() == PROMPT


def test_input_language_several_plugins():
    validator = ValidatePluginChoice(["1", PROMPT, "2"])
    patch_validator = patch("rpdk.core.init.validate_plugin_choice", validator)
    patch_input = patch("rpdk.core.init.input", return_value="2")
    with patch_validator, patch_input as mock_input:
        assert input_language() == PROMPT

    mock_input.assert_called_once()
