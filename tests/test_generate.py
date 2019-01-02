from unittest.mock import Mock, patch

import pytest

from rpdk.cli import main
from rpdk.project import Project


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
