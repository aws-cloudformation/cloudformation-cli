from unittest.mock import Mock, patch

import pytest
from jsonschema.exceptions import ValidationError

from rpdk.cli import main
from rpdk.project import Project


def test_validate_command_help(capsys):
    with patch("rpdk.validate.validate", autospec=True) as mock_validate:
        with pytest.raises(SystemExit):
            main(args_in=["validate", "--help"])  # init has no required params

    out, err = capsys.readouterr()
    assert not err
    assert "--help" in out
    mock_validate.assert_not_called()


def test_validate_command_project_not_found(capsys):
    mock_project = Mock(spec=Project)
    mock_project.load_settings.side_effect = FileNotFoundError

    with patch("rpdk.validate.Project", autospec=True, return_value=mock_project):
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=["validate"])

    assert excinfo.value.code == 1
    mock_project.load_settings.assert_called_once_with()
    mock_project.load_schema.assert_not_called()

    out, err = capsys.readouterr()
    assert not err
    assert "not found" in out
    assert "init" in out


def test_validate_command_invalid_schema(capsys):
    mock_project = Mock(spec=Project)
    mock_project.load_schema.side_effect = ValidationError("")

    with patch("rpdk.validate.Project", autospec=True, return_value=mock_project):
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=["validate"])

    assert excinfo.value.code == 1
    mock_project.load_settings.assert_called_once_with()
    mock_project.load_schema.assert_called_once_with()

    out, err = capsys.readouterr()
    assert not err
    assert "failed" in out


def test_validate_command_valid_schema(capsys):
    mock_project = Mock(spec=Project)

    with patch("rpdk.validate.Project", autospec=True, return_value=mock_project):
        main(args_in=["validate"])

    mock_project.load_settings.assert_called_once_with()
    mock_project.load_schema.assert_called_once_with()

    out, err = capsys.readouterr()
    assert not err
    assert "failed" not in out
