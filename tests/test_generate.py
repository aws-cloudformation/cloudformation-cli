from unittest.mock import Mock, patch

import pytest
from jsonschema.exceptions import ValidationError

from rpdk.cli import main
from rpdk.project import Project


def test_generate_command_help(capsys):
    with patch("rpdk.generate.generate", autospec=True) as mock_generate:
        with pytest.raises(SystemExit):
            main(args_in=["generate", "--help"])  # generate has no required params

    out, err = capsys.readouterr()
    assert not err
    assert "--help" in out
    mock_generate.assert_not_called()


def test_generate_command_project_not_found(capsys):
    mock_project = Mock(spec=Project)
    mock_project.load_settings.side_effect = FileNotFoundError

    with patch("rpdk.generate.Project", autospec=True, return_value=mock_project):
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=["generate"])

    assert excinfo.value.code == 1
    mock_project.load_settings.assert_called_once_with()
    mock_project.load_schema.assert_not_called()
    mock_project.generate.assert_not_called()

    out, err = capsys.readouterr()
    assert not err
    assert "not found" in out
    assert "init" in out


def test_generate_command_schema_not_found(capsys):
    mock_project = Mock(spec=Project)
    mock_project.load_schema.side_effect = FileNotFoundError

    with patch("rpdk.generate.Project", autospec=True, return_value=mock_project):
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=["generate"])

    assert excinfo.value.code == 1
    mock_project.load_settings.assert_called_once_with()
    mock_project.load_schema.assert_called_once_with()
    mock_project.generate.assert_not_called()

    out, err = capsys.readouterr()
    assert not err
    assert "not found" in out


def test_generate_command_invalid_schema(capsys):
    mock_project = Mock(spec=Project)
    mock_project.load_schema.side_effect = ValidationError("")

    with patch("rpdk.generate.Project", autospec=True, return_value=mock_project):
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=["generate"])

    assert excinfo.value.code == 1
    mock_project.load_settings.assert_called_once_with()
    mock_project.load_schema.assert_called_once_with()
    mock_project.generate.assert_not_called()

    out, err = capsys.readouterr()
    assert not err
    assert "invalid" in out


def test_generate_command_generate(capsys):
    mock_project = Mock(spec=Project)

    with patch("rpdk.generate.Project", autospec=True, return_value=mock_project):
        main(args_in=["generate"])

    mock_project.load_settings.assert_called_once_with()
    mock_project.load_schema.assert_called_once_with()
    mock_project.generate.assert_called_once_with()

    out, err = capsys.readouterr()
    assert not err
    assert not out
