from unittest.mock import Mock, patch

from rpdk.cli import main
from rpdk.project import Project


def test_package_command_default():
    mock_project = Mock(spec=Project)
    with patch("rpdk.package.Project", autospec=True, return_value=mock_project):
        main(args_in=["package"])
    mock_project.package.assert_called_once_with()
