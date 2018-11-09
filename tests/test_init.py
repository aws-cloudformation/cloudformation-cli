import os
import os.path
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from rpdk.cli import main
from rpdk.plugin_registry import _PLUGIN_DEFAULT

from .test_plugin_base import TestLanguagePlugin


@contextmanager
def chdir(path):
    old = os.getcwd()
    os.chdir(path)
    yield path
    os.chdir(old)


def test_init_command_help(capsys):
    with patch("rpdk.init.get_plugin", autospec=True) as mock_plugin:
        with pytest.raises(SystemExit):
            main(args_in=["init", "--help"])  # init has no required params
    out, _ = capsys.readouterr()
    assert "--help" in out
    mock_plugin.assert_not_called()


def test_init_command_default(tmpdir):
    plugin = TestLanguagePlugin()
    with patch(
        "rpdk.init.get_plugin", autospec=True, return_value=plugin
    ) as mock_plugin:
        with chdir(tmpdir.mkdir("init")) as cwd:  # equivalent to cd
            main(args_in=["init"])
    assert os.path.isfile(cwd.join("initech.tps.report.v1.json"))
    mock_plugin.assert_called_once_with(_PLUGIN_DEFAULT)
