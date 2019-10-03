# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from rpdk.core.cli import main
from rpdk.core.contract.interface import Action
from rpdk.core.contract.resource_client import ResourceClient
from rpdk.core.invoke import _needs_reinvocation
from rpdk.core.project import Project


@pytest.fixture
def payload_path(tmp_path):
    path = tmp_path / "payload.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "desiredResourceState": None,
                "previousResourceState": None,
                "logicalResourceIdentifier": None,
            },
            f,
        )
    return path


@pytest.fixture
def invalid_payload(tmp_path):
    path = tmp_path / "payload.json"
    with path.open("w", encoding="utf-8") as f:
        f.write("{,}")
    return path


@pytest.mark.parametrize("command", list(Action.__members__))
def test_invoke_command_happy_path(capsys, payload_path, command):
    mock_project, mock_client = _invoke_and_expect("SUCCESS", payload_path, command)

    mock_project.load.assert_called_once_with()
    mock_client.assert_called_once()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", list(Action.__members__))
def test_invoke_command_sad_path(capsys, payload_path, command):
    mock_project, mock_client = _invoke_and_expect("FAILED", payload_path, command)

    mock_project.load.assert_called_once_with()
    mock_client.assert_called_once()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", list(Action.__members__))
def test_invoke_command_in_progress_with_reinvoke(capsys, payload_path, command):
    mock_project, mock_client = _invoke_and_expect(
        "IN_PROGRESS", payload_path, command, "--max-reinvoke", "2"
    )

    assert mock_client.call_count == 3

    mock_project.load.assert_called_once_with()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", list(Action.__members__))
def test_invoke_command_in_progress_with_no_reinvocation(capsys, payload_path, command):
    mock_project, mock_client = _invoke_and_expect(
        "IN_PROGRESS", payload_path, command, "--max-reinvoke", "0"
    )

    assert mock_client.call_count == 1

    mock_project.load.assert_called_once_with()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", list(Action.__members__))
def test_value_error_on_json_load(capsys, invalid_payload, command):
    mock_project = Mock(spec=Project)
    mock_project.schema = {}
    mock_project.root = None

    patch_project = patch(
        "rpdk.core.invoke.Project", autospec=True, return_value=mock_project
    )

    with pytest.raises(SystemExit), patch_project:
        main(args_in=["invoke", command, str(invalid_payload)])

    out, _err = capsys.readouterr()
    assert "Invalid JSON" in out


@pytest.mark.parametrize("command", list(Action.__members__))
def test_keyboard_interrupt(capsys, payload_path, command):
    mock_project = Mock(spec=Project)
    mock_project.schema = {}
    mock_project.root = None

    patch_project = patch(
        "rpdk.core.invoke.Project", autospec=True, return_value=mock_project
    )

    json_patch = patch.object(json, "dumps", side_effect=KeyboardInterrupt)
    mock_client_call = MagicMock(return_value={"status": "SUCCESS"})
    patch_client_call = patch.object(ResourceClient, "_call", mock_client_call)

    with patch_project, patch_client_call, json_patch:
        main(args_in=["invoke", command, str(payload_path)])

    assert mock_client_call.call_count == 0

    mock_project.load.assert_called_once_with()
    _out, err = capsys.readouterr()
    assert not err


# We test this private member directly because it is not practical to
# test the case where IN_PROGRESS re-invokes indefinitely.
def test_needs_reinvocation():
    assert _needs_reinvocation(None, 300)
    assert _needs_reinvocation(None, 0)
    assert _needs_reinvocation(1, 0)
    assert _needs_reinvocation(1, 1)
    assert not _needs_reinvocation(1, 2)


def _invoke_and_expect(status, payload_path, command, *args):
    mock_project = Mock(spec=Project)
    mock_project.schema = {}
    mock_project.root = None

    patch_project = patch(
        "rpdk.core.invoke.Project", autospec=True, return_value=mock_project
    )

    mock_client_call = MagicMock(return_value={"status": status})

    patch_client_call = patch.object(ResourceClient, "_call", mock_client_call)

    with patch_project, patch_client_call as mock_client:
        main(args_in=["invoke", command, str(payload_path), *args])

    return mock_project, mock_client
