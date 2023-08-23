from unittest.mock import MagicMock, patch

from rpdk.core.extensions import setup_subparsers


def test_setup_subparsers():
    expeted_command_name = "expected-command-name"

    mock_extension = MagicMock()
    mock_extension.command_name = expeted_command_name

    mock_extension_entry_point = MagicMock()
    mock_extension_entry_point.return_value.return_value = mock_extension

    mock_extension_entry_points = {"key": mock_extension_entry_point}

    subparsers, parents, parser = MagicMock(), MagicMock(), MagicMock()
    subparsers.add_parser.return_value = parser

    with patch("rpdk.core.extensions.get_extensions") as mock_get_extensions:
        mock_get_extensions.return_value = mock_extension_entry_points
        setup_subparsers(subparsers, parents)

    mock_extension.setup_parser.assert_called_once_with(parser)
    subparsers.add_parser.assert_called_with(expeted_command_name, parents=parents)
