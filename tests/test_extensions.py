import argparse
from unittest import TestCase
from unittest.mock import MagicMock, patch

from rpdk.core.extensions import setup_subparsers


class ExtensionTest(TestCase):
    def test_setup_subparsers(self):
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

    def test_setup_subparsers_should_raise_error_when_collision_occur(self):
        command_name = "command-name"

        mock_extension_1, mock_extension_2 = MagicMock(), MagicMock()
        mock_extension_1.command_name = command_name
        mock_extension_2.command_name = command_name

        mock_extension_1_entry_point = MagicMock()
        mock_extension_1_entry_point.return_value.return_value = mock_extension_1

        mock_extension_2_entry_point = MagicMock()
        mock_extension_2_entry_point.return_value.return_value = mock_extension_2

        mock_extension_entry_points = {
            "key_1": mock_extension_1_entry_point,
            "key_2": mock_extension_2_entry_point,
        }

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        with patch(
            "rpdk.core.extensions.get_extensions"
        ) as mock_get_extensions, self.assertRaises(RuntimeError) as context:
            mock_get_extensions.return_value = mock_extension_entry_points
            setup_subparsers(subparsers, [])

        assert (
            str(context.exception)
            == '"command-name" is already registered as an extension. Please use a'
            " different name."
        )
