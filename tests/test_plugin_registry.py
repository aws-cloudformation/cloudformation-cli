from unittest.mock import Mock, patch

from rpdk.core.plugin_registry import load_plugin


def test_load_plugin():
    plugin = Mock()
    with patch.dict(
        "rpdk.core.plugin_registry.PLUGIN_REGISTRY", {"test": plugin}, clear=True
    ):
        load_plugin("test")
    plugin.assert_called_once_with()
    plugin.return_value.assert_called_once_with()
