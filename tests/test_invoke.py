# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import json
from io import StringIO
from unittest.mock import Mock, patch

import pytest

from rpdk.core.cli import main
from rpdk.core.contract.interface import Action
from rpdk.core.invoke import _needs_reinvocation
from rpdk.core.project import Project

ACTIONS = list(Action.__members__)


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


@pytest.mark.parametrize("command", ACTIONS)
def test_invoke_command_happy_path(capsys, payload_path, command):
    mock_project, mock_invoke = _invoke_and_expect("SUCCESS", payload_path, command)

    mock_project.load.assert_called_once_with()
    mock_invoke.assert_called_once()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", ACTIONS)
def test_invoke_command_sad_path(capsys, payload_path, command):
    mock_project, mock_invoke = _invoke_and_expect("FAILED", payload_path, command)

    mock_project.load.assert_called_once_with()
    mock_invoke.assert_called_once()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", ACTIONS)
def test_invoke_command_in_progress_with_reinvoke(capsys, payload_path, command):
    mock_project, mock_invoke = _invoke_and_expect(
        "IN_PROGRESS", payload_path, command, "--max-reinvoke", "2"
    )

    assert mock_invoke.call_count == 3

    mock_project.load.assert_called_once_with()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", ACTIONS)
def test_invoke_command_in_progress_with_no_reinvocation(capsys, payload_path, command):
    mock_project, mock_invoke = _invoke_and_expect(
        "IN_PROGRESS", payload_path, command, "--max-reinvoke", "0"
    )

    mock_project.load.assert_called_once_with()
    mock_invoke.assert_called_once()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", ACTIONS)
def test_value_error_on_json_load(capsys, invalid_payload, command):
    mock_project = Mock(spec=Project)
    mock_project.schema = {}
    mock_project.root = None

    patch_project = patch(
        "rpdk.core.invoke.Project", autospec=True, return_value=mock_project
    )
    patch_session = patch(
        "rpdk.core.contract.resource_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )

    with patch_project, patch_session, patch_creds:
        with pytest.raises(SystemExit):
            main(args_in=["invoke", command, str(invalid_payload)])

    out, _err = capsys.readouterr()
    assert "Invalid JSON" in out


@pytest.mark.parametrize("command", ACTIONS)
def test_keyboard_interrupt(capsys, payload_path, command):
    mock_project = Mock(spec=Project)
    mock_project.schema = {}
    mock_project.root = None

    patch_project = patch(
        "rpdk.core.invoke.Project", autospec=True, return_value=mock_project
    )
    patch_session = patch(
        "rpdk.core.contract.resource_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )
    patch_dumps = patch.object(json, "dumps", side_effect=KeyboardInterrupt)

    with patch_project, patch_creds, patch_dumps, patch_session as mock_session:
        mock_client = mock_session.return_value.client.return_value
        main(args_in=["invoke", command, str(payload_path)])

    mock_project.load.assert_called_once_with()
    mock_client.invoke.assert_not_called()
    _out, err = capsys.readouterr()
    assert not err


# We test this private member directly because it is not practical to
# test the case where IN_PROGRESS re-invokes indefinitely.
@pytest.mark.parametrize(
    "max_reinvoke,current_invocation,result",
    [(None, 300, True), (None, 0, True), (1, 0, True), (1, 1, True), (1, 2, False)],
)
def test_needs_reinvocation(max_reinvoke, current_invocation, result):
    assert _needs_reinvocation(max_reinvoke, current_invocation) is result


def _invoke_and_expect(status, payload_path, command, *args):
    mock_project = Mock(spec=Project)
    mock_project.schema = {}
    mock_project.root = None

    patch_project = patch(
        "rpdk.core.invoke.Project", autospec=True, return_value=mock_project
    )
    patch_session = patch(
        "rpdk.core.contract.resource_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.resource_client.get_temporary_credentials",
        autospec=True,
        return_value={},
    )

    with patch_project, patch_session as mock_session, patch_creds as mock_creds:
        mock_client = mock_session.return_value.client.return_value
        mock_client.invoke.side_effect = lambda **_kwargs: {
            "Payload": StringIO(json.dumps({"status": status}))
        }
        main(args_in=["invoke", command, str(payload_path), *args])

    mock_creds.assert_called_once()

    return mock_project, mock_client.invoke
