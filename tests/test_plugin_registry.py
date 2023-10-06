from unittest.mock import Mock, patch

from rpdk.core.plugin_registry import get_extensions, load_plugin


def test_load_plugin():
    plugin = Mock()
    with patch.dict(
        "rpdk.core.plugin_registry.PLUGIN_REGISTRY", {"test": plugin}, clear=True
    ):
        load_plugin("test")
    plugin.assert_called_once_with()
    plugin.return_value.assert_called_once_with()


def test_get_extensions():
    mock_entrypoint_1 = Mock()
    mock_entrypoint_2 = Mock()

    patch_iter_entry_points = patch(
        "rpdk.core.plugin_registry.pkg_resources.iter_entry_points"
    )
    with patch_iter_entry_points as mock_iter_entry_points:
        mock_iter_entry_points.return_value = [mock_entrypoint_1, mock_entrypoint_2]

        extensions = get_extensions()

    assert extensions == {
        mock_entrypoint_1.name: mock_entrypoint_1.load,
        mock_entrypoint_2.name: mock_entrypoint_2.load,
    }
