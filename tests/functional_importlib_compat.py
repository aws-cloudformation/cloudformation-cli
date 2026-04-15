"""
Integration test: validates that data_loaders and plugin_registry work correctly
without pkg_resources, using only importlib.resources / importlib.metadata.

Run with:
    pytest tests/functional_importlib_compat.py -v
"""
import sys
import importlib
import pytest


def test_no_pkg_resources_imported_by_data_loaders():
    """data_loaders must not import pkg_resources at all."""
    # Force reimport to catch top-level imports
    if "rpdk.core.data_loaders" in sys.modules:
        del sys.modules["rpdk.core.data_loaders"]

    import unittest.mock as mock
    with mock.patch.dict("sys.modules", {"pkg_resources": None}):
        # Should not raise ModuleNotFoundError
        import rpdk.core.data_loaders  # noqa: F401


def test_no_pkg_resources_imported_by_plugin_registry():
    """plugin_registry must not import pkg_resources at all."""
    if "rpdk.core.plugin_registry" in sys.modules:
        del sys.modules["rpdk.core.plugin_registry"]

    import unittest.mock as mock
    with mock.patch.dict("sys.modules", {"pkg_resources": None}):
        import rpdk.core.plugin_registry  # noqa: F401


def test_resource_json_loads_real_schema():
    """resource_json must load an actual bundled schema file end-to-end."""
    from rpdk.core.data_loaders import resource_json
    schema = resource_json(
        "rpdk.core", "data/schema/provider.definition.schema.v1.json"
    )
    assert "$schema" in schema or "properties" in schema


def test_resource_stream_returns_readable_content():
    """resource_stream must return a readable text stream for a bundled file."""
    from rpdk.core.data_loaders import resource_stream
    with resource_stream(
        "rpdk.core", "data/schema/provider.definition.schema.v1.json"
    ) as f:
        content = f.read()
    assert len(content) > 0
    assert "$schema" in content or "properties" in content


def test_plugin_registry_get_plugin_choices_does_not_raise():
    """get_plugin_choices must not raise even with no plugins installed."""
    from rpdk.core.plugin_registry import get_plugin_choices
    choices = get_plugin_choices()
    assert isinstance(choices, list)


def test_importlib_resources_files_available():
    """Verify the compat shim resolves correctly on this Python version."""
    if sys.version_info >= (3, 9):
        from importlib.resources import files
    else:
        from importlib_resources import files
    assert callable(files)
