from unittest.mock import MagicMock, patch

from rpdk.core.extensions import setup_subparsers


def test_setup_subparsers():
    patch_get_extensions = patch("rpdk.core.extensions.get_extensions")

    subparsers, parents = MagicMock(), MagicMock()

    with patch_get_extensions as mock_get_extensions:
        mock_extension_entry_point = MagicMock()
        extensions = {"key": mock_extension_entry_point}
        mock_get_extensions.return_value = extensions
        setup_subparsers(subparsers, parents)

    mock_extension = mock_extension_entry_point.return_value.return_value
    mock_extension.setup_subparser.assert_called_once_with(subparsers, parents)
