from unittest.mock import Mock, patch

from rpdk.plugin_registry import get_plugin


def test_get_plugin():
    plugin = Mock()
    with patch.dict(
        "rpdk.plugin_registry.PLUGIN_REGISTRY", {"test": plugin}, clear=True
    ):
        get_plugin("test")
    plugin.assert_called_once_with()
    plugin.return_value.assert_called_once_with()
