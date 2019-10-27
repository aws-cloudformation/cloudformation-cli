# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from rpdk.core.cli import EXIT_UNHANDLED_EXCEPTION, main
from rpdk.core.contract.interface import Action
from rpdk.core.project import Project
from rpdk.core.test import (
    DEFAULT_ENDPOINT,
    DEFAULT_FUNCTION,
    DEFAULT_REGION,
    empty_override,
    get_marker_options,
    get_overrides,
    temporary_ini_file,
)

RANDOM_INI = "pytest_SOYPKR.ini"
EMPTY_OVERRIDE = empty_override()


SCHEMA = {"handlers": {action.lower(): [] for action in Action}}


@contextmanager
def mock_temporary_ini_file():
    yield RANDOM_INI


@pytest.mark.parametrize(
    "args_in,pytest_args,plugin_args",
    [
        ([], [], [DEFAULT_FUNCTION, DEFAULT_ENDPOINT, DEFAULT_REGION]),
        (["--endpoint", "foo"], [], [DEFAULT_FUNCTION, "foo", DEFAULT_REGION]),
        (["--function-name", "bar"], [], ["bar", DEFAULT_ENDPOINT, DEFAULT_REGION]),
        (
            ["--", "-k", "create"],
            ["-k", "create"],
            [DEFAULT_FUNCTION, DEFAULT_ENDPOINT, DEFAULT_REGION],
        ),
        (
            ["--region", "us-west-2", "--", "--collect-only"],
            ["--collect-only"],
            [DEFAULT_FUNCTION, DEFAULT_ENDPOINT, "us-west-2"],
        ),
    ],
)
def test_test_command_happy_path(
    capsys, args_in, pytest_args, plugin_args
):  # pylint: disable=too-many-locals
    mock_project = Mock(spec=Project)
    mock_project.schema = SCHEMA
    mock_project.root = None

    patch_project = patch(
        "rpdk.core.test.Project", autospec=True, return_value=mock_project
    )
    patch_plugin = patch("rpdk.core.test.ContractPlugin", autospec=True)
    patch_client = patch("rpdk.core.test.ResourceClient", autospec=True)
    patch_pytest = patch("rpdk.core.test.pytest.main", autospec=True, return_value=0)
    patch_ini = patch(
        "rpdk.core.test.temporary_ini_file", side_effect=mock_temporary_ini_file
    )
    # fmt: off
    with patch_project, \
            patch_plugin as mock_plugin, \
            patch_client as mock_client, \
            patch_pytest as mock_pytest, \
            patch_ini as mock_ini:
        main(args_in=["test"] + args_in)
    # fmt: on

    mock_project.load.assert_called_once_with()
    function_name, endpoint, region = plugin_args
    mock_client.assert_called_once_with(
        function_name, endpoint, region, mock_project.schema, EMPTY_OVERRIDE, None
    )
    mock_plugin.assert_called_once_with(mock_client.return_value)
    mock_ini.assert_called_once_with()
    mock_pytest.assert_called_once_with(
        ["-c", RANDOM_INI, "-m", ""] + pytest_args, plugins=[mock_plugin.return_value]
    )

    _out, err = capsys.readouterr()
    assert not err


def test_test_command_return_code_on_error():
    mock_project = Mock(spec=Project)

    mock_project.root = None
    mock_project.schema = SCHEMA
    patch_project = patch(
        "rpdk.core.test.Project", autospec=True, return_value=mock_project
    )
    patch_plugin = patch("rpdk.core.test.ContractPlugin", autospec=True)
    patch_client = patch("rpdk.core.test.ResourceClient", autospec=True)
    patch_pytest = patch("rpdk.core.test.pytest.main", autospec=True, return_value=1)
    with patch_project, patch_plugin, patch_client, patch_pytest:
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=["test"])

    assert excinfo.value.code != EXIT_UNHANDLED_EXCEPTION


def test_temporary_ini_file():
    with temporary_ini_file() as path_str:
        assert isinstance(path_str, str)
        path = Path(path_str)
        assert path.name.startswith("pytest_")
        assert path.name.endswith(".ini")

        with path.open("r", encoding="utf-8") as f:
            assert "[pytest]" in f.read()


def test_get_overrides_no_root():
    assert get_overrides(None) == EMPTY_OVERRIDE


@pytest.fixture
def base(tmpdir):
    return Path(tmpdir)


def test_get_overrides_file_not_found(base):
    path = base / "overrides.json"
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    assert get_overrides(path) == EMPTY_OVERRIDE


def test_get_overrides_invalid_file(base):
    path = base / "overrides.json"
    path.write_text("{}")
    assert get_overrides(base) == EMPTY_OVERRIDE


def test_get_overrides_empty_overrides(base):
    path = base / "overrides.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(EMPTY_OVERRIDE, f)
    assert get_overrides(base) == EMPTY_OVERRIDE


def test_get_overrides_invalid_pointer_skipped(base):
    overrides = empty_override()
    overrides["CREATE"]["#/foo/bar"] = None

    path = base / "overrides.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(overrides, f)
    assert get_overrides(base) == EMPTY_OVERRIDE


def test_get_overrides_good_path(base):
    overrides = empty_override()
    overrides["CREATE"]["/foo/bar"] = {}

    path = base / "overrides.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(overrides, f)
    assert get_overrides(base) == {"CREATE": {("foo", "bar"): {}}}


@pytest.mark.parametrize(
    "schema,expected_marker_keywords",
    [
        (SCHEMA, ""),
        (
            {"handlers": {"create": [], "read": [], "update": [], "delete": []}},
            ("not list",),
        ),
        (
            {"handlers": {"create": []}},
            ("not read", "not update", "not delete", "not list", " and "),
        ),
    ],
)
def test_get_marker_options(schema, expected_marker_keywords):
    marker_options = get_marker_options(schema)
    assert all(keyword in marker_options for keyword in expected_marker_keywords)
