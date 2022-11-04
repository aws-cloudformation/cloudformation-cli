from unittest.mock import Mock, patch

from rpdk.core.cli import main
from rpdk.core.project import Project


def test_package_command_valid_schema():
    mock_project = Mock(spec=Project)

    with patch("rpdk.core.package.Project", autospec=True, return_value=mock_project):
        main(args_in=["package"])

    mock_project.load.assert_called_once()
    mock_project.submit.assert_called_once_with(
        dry_run=True,
        endpoint_url=False,
        region_name=False,
        role_arn=False,
        use_role=False,
        set_default=False,
    )
