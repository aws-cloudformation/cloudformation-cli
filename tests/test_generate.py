from unittest.mock import Mock, patch

from rpdk.cli import main
from rpdk.project import Project


def test_generate_command_generate(capsys):
    mock_project = Mock(spec=Project)

    with patch("rpdk.generate.Project", autospec=True, return_value=mock_project):
        main(args_in=["generate"])

    mock_project.load.assert_called_once_with()
    mock_project.generate.assert_called_once_with()

    out, err = capsys.readouterr()
    assert not err
    assert not out
