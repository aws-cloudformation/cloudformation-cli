from unittest.mock import Mock, patch

import pytest

from rpdk.cli import main
from rpdk.project import Project


def test_package_command_help(capsys):
    with patch("rpdk.package.package", autospec=True):
        with pytest.raises(SystemExit):
            main(args_in=["package", "--help"])
    out, _ = capsys.readouterr()
    assert "--help" in out


def test_package_command_project_not_found(capsys):
    mock_project = Mock(spec=Project)
    mock_project.load_settings.side_effect = FileNotFoundError

    with patch("rpdk.package.Project", autospec=True, return_value=mock_project):
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=["package", "SomeHandler"])

    assert excinfo.value.code == 1
    mock_project.load_settings.assert_called_once_with()
    mock_project.package.assert_not_called()

    out, err = capsys.readouterr()
    assert not err
    assert "not found" in out
    assert "init" in out


def test_package_command_default():
    handler_path = "Handler.path"
    mock_project = Mock(spec=Project)
    with patch("rpdk.package.Project", autospec=True, return_value=mock_project):
        main(args_in=["package", handler_path])
    mock_project.package.assert_called_once_with(handler_path)
