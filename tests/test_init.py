from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import ANY, Mock, PropertyMock, patch

import pytest

from rpdk.core.cli import main
from rpdk.core.exceptions import WizardAbortError, WizardValidationError
from rpdk.core.init import (
    ValidatePluginChoice,
    check_for_existing_project,
    ignore_abort,
    input_language,
    input_with_validation,
    validate_type_name,
    validate_yes,
)
from rpdk.core.module.init_module import input_typename as input_typename_module
from rpdk.core.project import Project
from rpdk.core.resource.init_resource import input_typename as input_typename_resource

from .utils import add_dummy_language_plugin, dummy_parser, get_args, get_mock_project

PROMPT = "MECVGD"
ERROR = "TUJFEL"


def test_init_resource_method_interactive():
    type_name = object()
    language = object()

    mock_project, patch_project = get_mock_project()
    patch_tn = patch(
        "rpdk.core.resource.init_resource.input_typename", return_value=type_name
    )
    patch_l = patch(
        "rpdk.core.resource.init_resource.input_language", return_value=language
    )
    patch_at = patch("rpdk.core.init.init_artifact_type", return_value="RESOURCE")

    with patch_project, patch_at as mock_t, patch_tn as mock_tn, patch_l as mock_l:
        main(args_in=["init"])

    mock_tn.assert_called_once_with()
    mock_l.assert_called_once_with()
    mock_t.assert_called_once()

    mock_project.load_settings.assert_called_once_with()
    mock_project.init.assert_called_once_with(
        type_name,
        language,
        {
            "version": False,
            "subparser_name": None,
            "verbose": 0,
            "force": False,
            "type_name": None,
            "artifact_type": None,
        },
    )
    mock_project.generate.assert_called_once_with()


def test_init_module_method_interactive():
    type_name = object()
    language = object()

    mock_project, patch_project = get_mock_project()

    patch_tn = patch(
        "rpdk.core.module.init_module.input_typename", return_value=type_name
    )
    patch_l = patch(
        "rpdk.core.resource.init_resource.input_language", return_value=language
    )
    patch_at = patch("rpdk.core.init.init_artifact_type", return_value="MODULE")

    with TemporaryDirectory() as temporary_directory:
        mock_project.root = Path(temporary_directory)
        with patch_project, patch_tn as mock_tn, patch_l as mock_l, patch_at as mock_t:
            main(args_in=["init"])

    mock_tn.assert_called_once_with()
    mock_l.assert_not_called()
    mock_t.assert_called_once()

    mock_project.load_settings.assert_called_once_with()
    mock_project.init_module.assert_called_once_with(type_name)
    mock_project.generate.assert_not_called()


def test_init_resource_method_noninteractive():
    add_dummy_language_plugin()
    artifact_type = "RESOURCE"
    args = get_args("dummy", "Test::Test::Test", artifact_type)
    mock_project, patch_project = get_mock_project()

    patch_get_parser = patch(
        "rpdk.core.init.get_parsers", return_value={"dummy": dummy_parser}
    )

    with patch_project, patch_get_parser as mock_parser:
        main(
            args_in=[
                "init",
                "--type-name",
                args.type_name,
                "--artifact-type",
                args.artifact_type,
                args.language,
                "--dummy",
            ]
        )

    mock_parser.assert_called_once()

    mock_project.load_settings.assert_called_once_with()
    mock_project.init.assert_called_once_with(
        args.type_name,
        args.language,
        {
            "version": False,
            "subparser_name": args.language,
            "verbose": 0,
            "force": False,
            "type_name": args.type_name,
            "language": args.language,
            "dummy": True,
            "artifact_type": artifact_type,
        },
    )
    mock_project.generate.assert_called_once_with()


def test_init_resource_method_noninteractive_invalid_type_name():
    add_dummy_language_plugin()
    type_name = object()
    artifact_type = "RESOURCE"

    args = get_args("dummy", "invalid_type_name", "RESOURCE")
    mock_project, patch_project = get_mock_project()

    patch_tn = patch(
        "rpdk.core.resource.init_resource.input_typename", return_value=type_name
    )
    patch_t = patch("rpdk.core.init.init_artifact_type", return_value=artifact_type)
    patch_get_parser = patch(
        "rpdk.core.init.get_parsers", return_value={"dummy": dummy_parser}
    )

    with patch_project, patch_t, patch_tn as mock_tn, patch_get_parser as mock_parser:
        main(
            args_in=[
                "init",
                "-t",
                args.type_name,
                "-a",
                args.artifact_type,
                args.language,
                "--dummy",
            ]
        )

    mock_tn.assert_called_once_with()
    mock_parser.assert_called_once()

    mock_project.load_settings.assert_called_once_with()
    mock_project.init.assert_called_once_with(
        type_name,
        args.language,
        {
            "version": False,
            "subparser_name": args.language,
            "verbose": 0,
            "force": False,
            "type_name": args.type_name,
            "artifact_type": artifact_type,
            "dummy": True,
            "language": args.language,
        },
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


def test_init_module_method_noninteractive():
    add_dummy_language_plugin()
    artifact_type = "MODULE"
    args = get_args("dummy", "Test::Test::Test::MODULE", artifact_type)
    mock_project, patch_project = get_mock_project()

    patch_get_parser = patch(
        "rpdk.core.init.get_parsers", return_value={"dummy": dummy_parser}
    )

    with TemporaryDirectory() as temporary_directory:
        mock_project.root = Path(temporary_directory)
        with patch_project, patch_get_parser as mock_parser:
            main(
                args_in=[
                    "init",
                    "--type-name",
                    args.type_name,
                    "--artifact-type",
                    args.artifact_type,
                    args.language,
                    "--dummy",
                ]
            )

    mock_parser.assert_called_once()

    mock_project.load_settings.assert_called_once_with()
    mock_project.init_module.assert_called_once_with(args.type_name)
    mock_project.generate.assert_not_called()


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
        "rpdk.core.init.input_with_validation", autospec=True, return_value="m"
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


def test_input_typename_resource():
    type_name = "AWS::Color::Red"
    patch_input = patch("rpdk.core.utils.init_utils.input", return_value=type_name)
    with patch_input as mock_input:
        assert input_typename_resource() == type_name
    mock_input.assert_called_once()


def test_input_typename_module():
    type_name = "AWS::Color::Red::MODULE"
    patch_input = patch("rpdk.core.utils.init_utils.input", return_value=type_name)
    with patch_input as mock_input:
        assert input_typename_module() == type_name
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
