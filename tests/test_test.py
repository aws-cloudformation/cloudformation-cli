from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from rpdk.core.cli import main
from rpdk.core.project import Project
from rpdk.core.test import temporary_ini_file

RANDOM_INI = "pytest_SOYPKR.ini"
EXPECTED_PYTEST_ARGS = ["-c", RANDOM_INI]


@contextmanager
def mock_temporary_ini_file():
    yield RANDOM_INI


@pytest.mark.parametrize(
    "args_in,pytest_args",
    [
        ([], []),
        (["--test-types", "create"], ["-k", "create"]),
        (["--collect-only"], ["--collect-only"]),
        (
            ["--collect-only", "--test-types", "create"],
            ["-k", "create", "--collect-only"],
        ),
    ],
)
def test_test_command(capsys, args_in, pytest_args):
    mock_project = Mock(spec=Project)
    mock_project.schema = {}

    patch_project = patch(
        "rpdk.core.test.Project", autospec=True, return_value=mock_project
    )
    patch_plugin = patch("rpdk.core.test.ContractPlugin", autospec=True)
    patch_pytest = patch("rpdk.core.test.pytest.main", autospec=True)
    patch_ini = patch(
        "rpdk.core.test.temporary_ini_file", side_effect=mock_temporary_ini_file
    )
    # fmt: off
    with patch_project, \
            patch_plugin as mock_plugin, \
            patch_pytest as mock_pytest, \
            patch_ini as mock_ini:
        main(args_in=["test"] + args_in)
    # fmt: on

    mock_project.load.assert_called_once_with()
    mock_plugin.assert_called_once_with(
        "TestEntrypoint", "http://127.0.0.1:3001", "us-east-1", mock_project.schema
    )
    mock_ini.assert_called_once_with()
    mock_pytest.assert_called_once_with(
        ["-c", RANDOM_INI] + pytest_args, plugins=[mock_plugin.return_value]
    )

    _out, err = capsys.readouterr()
    assert not err


def test_temporary_ini_file():
    with temporary_ini_file() as path_str:
        assert isinstance(path_str, str)
        path = Path(path_str)
        assert path.name.startswith("pytest_")
        assert path.name.endswith(".ini")

        with path.open("r", encoding="utf-8") as f:
            assert "[pytest]" in f.read()
