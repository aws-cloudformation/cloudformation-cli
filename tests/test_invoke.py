# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import json
from io import StringIO
from unittest.mock import Mock, patch

import pytest

from rpdk.core.cli import EXIT_UNHANDLED_EXCEPTION, main
from rpdk.core.contract.interface import Action, HookInvocationPoint
from rpdk.core.invoke import _needs_reinvocation
from rpdk.core.project import ARTIFACT_TYPE_HOOK, ARTIFACT_TYPE_RESOURCE, Project

ACTIONS = list(Action.__members__)
HOOK_INVOCATION_POINTS = list(HookInvocationPoint.__members__)


def _setup_resource_test():
    mock_project = Mock(spec=Project)
    mock_project.schema = {}
    mock_project.root = None
    mock_project.executable_entrypoint = None
    mock_project.artifact_type = ARTIFACT_TYPE_RESOURCE

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
    patch_account = patch(
        "rpdk.core.contract.resource_client.get_account",
        autospec=True,
        return_value="",
    )

    return mock_project, patch_project, patch_session, patch_creds, patch_account


def _setup_hook_test():
    mock_project = Mock(spec=Project)
    mock_project.schema = {}
    mock_project.root = None
    mock_project.executable_entrypoint = None
    mock_project.artifact_type = ARTIFACT_TYPE_HOOK

    patch_project = patch(
        "rpdk.core.invoke.Project", autospec=True, return_value=mock_project
    )
    patch_session = patch(
        "rpdk.core.contract.hook_client.create_sdk_session", autospec=True
    )
    patch_creds = patch(
        "rpdk.core.contract.hook_client.get_temporary_credentials",
        autospec=True,
        return_value="{}",
    )
    patch_account = patch(
        "rpdk.core.contract.hook_client.get_account",
        autospec=True,
        return_value="",
    )
    patch_type_name = patch(
        "rpdk.core.contract.hook_client.HookClient.get_hook_type_name",
        autospec=True,
        return_value="AWS::Testing::Hook",
    )

    return (
        mock_project,
        patch_project,
        patch_session,
        patch_creds,
        patch_account,
        patch_type_name,
    )


@pytest.fixture
def resource_payload_path(tmp_path):
    path = tmp_path / "payload.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "desiredResourceState": {"foo": "bar"},
                "previousResourceState": {"foo": "prev_bar"},
                "logicalResourceIdentifier": None,
            },
            f,
        )
    return path


@pytest.fixture
def hook_payload_path(tmp_path):
    path = tmp_path / "payload.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "targetName": "AWS::Testing::Resource",
                "targetModel": {"foo": "bar"},
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


@pytest.mark.parametrize("command", ["invalid"])
def test_command_with_invalid_subcommand(capsys, command):
    with patch("rpdk.core.invoke.invoke", autospec=True) as mock_func:
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=["invoke", command])
    assert excinfo.value.code != EXIT_UNHANDLED_EXCEPTION
    _, err = capsys.readouterr()
    assert "invalid choice:" in err
    mock_func.assert_not_called()


@pytest.mark.parametrize("command", ["resource", "hook"])
def test_subcommand_with_required_params(capsys, command):
    with patch("rpdk.core.invoke.invoke", autospec=True) as mock_func:
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=["invoke", command])
    assert excinfo.value.code != EXIT_UNHANDLED_EXCEPTION
    _, err = capsys.readouterr()
    assert "the following arguments are required" in err
    mock_func.assert_not_called()


@pytest.mark.parametrize("command", ACTIONS)
def test_invoke_command_happy_path_resource(capsys, resource_payload_path, command):
    mock_project, mock_invoke = _invoke_and_expect_resource(
        "SUCCESS", resource_payload_path, command
    )

    mock_project.load.assert_called_once_with()
    mock_invoke.assert_called_once()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", HOOK_INVOCATION_POINTS)
def test_invoke_command_happy_path_hook(capsys, hook_payload_path, command):
    mock_project, mock_invoke = _invoke_and_expect_hook(
        "SUCCESS", hook_payload_path, command
    )

    mock_project.load.assert_called_once_with()
    mock_invoke.assert_called_once()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", ACTIONS)
def test_invoke_command_sad_path_resource(capsys, resource_payload_path, command):
    mock_project, mock_invoke = _invoke_and_expect_resource(
        "FAILED", resource_payload_path, command
    )

    mock_project.load.assert_called_once_with()
    mock_invoke.assert_called_once()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", HOOK_INVOCATION_POINTS)
def test_invoke_command_sad_path_hook(capsys, hook_payload_path, command):
    mock_project, mock_invoke = _invoke_and_expect_hook(
        "FAILED", hook_payload_path, command
    )

    mock_project.load.assert_called_once_with()
    mock_invoke.assert_called_once()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", ACTIONS)
def test_invoke_command_in_progress_with_reinvoke_resource(
    capsys, resource_payload_path, command
):
    mock_project, mock_invoke = _invoke_and_expect_resource(
        "IN_PROGRESS", resource_payload_path, command, "--max-reinvoke", "2"
    )

    assert mock_invoke.call_count == 3

    mock_project.load.assert_called_once_with()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", HOOK_INVOCATION_POINTS)
def test_invoke_command_in_progress_with_reinvoke_hook(
    capsys, hook_payload_path, command
):
    mock_project, mock_invoke = _invoke_and_expect_hook(
        "IN_PROGRESS", hook_payload_path, command, "--max-reinvoke", "2"
    )

    assert mock_invoke.call_count == 3

    mock_project.load.assert_called_once_with()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", ACTIONS)
def test_invoke_command_in_progress_with_no_reinvocation_resource(
    capsys, resource_payload_path, command
):
    mock_project, mock_invoke = _invoke_and_expect_resource(
        "IN_PROGRESS", resource_payload_path, command, "--max-reinvoke", "0"
    )

    mock_project.load.assert_called_once_with()
    mock_invoke.assert_called_once()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", HOOK_INVOCATION_POINTS)
def test_invoke_command_in_progress_with_no_reinvocation_hook(
    capsys, hook_payload_path, command
):
    mock_project, mock_invoke = _invoke_and_expect_hook(
        "IN_PROGRESS", hook_payload_path, command, "--max-reinvoke", "0"
    )

    mock_project.load.assert_called_once_with()
    mock_invoke.assert_called_once()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", ACTIONS)
def test_value_error_on_json_load_resource(capsys, invalid_payload, command):
    (
        _mock_project,
        patch_project,
        patch_session,
        patch_creds,
        patch_account,
    ) = _setup_resource_test()

    with patch_project, patch_session, patch_creds, patch_account:
        with pytest.raises(SystemExit):
            main(args_in=["invoke", "resource", command, str(invalid_payload)])

    out, _err = capsys.readouterr()
    assert "Invalid JSON" in out


@pytest.mark.parametrize("command", HOOK_INVOCATION_POINTS)
def test_value_error_on_json_load_hook(capsys, invalid_payload, command):
    (
        _mock_project,
        patch_project,
        patch_session,
        patch_creds,
        patch_account,
        patch_type_name,
    ) = _setup_hook_test()

    with patch_project, patch_session, patch_creds, patch_account, patch_type_name:
        with pytest.raises(SystemExit):
            main(args_in=["invoke", "hook", command, str(invalid_payload)])

    out, _err = capsys.readouterr()
    assert "Invalid JSON" in out


@pytest.mark.parametrize("command", ACTIONS)
def test_keyboard_interrupt_resource(capsys, resource_payload_path, command):
    (
        mock_project,
        patch_project,
        patch_session,
        patch_creds,
        patch_account,
    ) = _setup_resource_test()

    patch_dumps = patch.object(json, "dumps", side_effect=KeyboardInterrupt)

    # fmt: off
    with patch_project, \
         patch_creds, \
         patch_dumps, \
         patch_account, \
         patch_session as mock_session:
        mock_client = mock_session.return_value.client.return_value
        main(args_in=["invoke", "resource", command, str(resource_payload_path)])
    # fmt: on

    mock_project.load.assert_called_once_with()
    mock_client.invoke.assert_not_called()
    _out, err = capsys.readouterr()
    assert not err


@pytest.mark.parametrize("command", HOOK_INVOCATION_POINTS)
def test_keyboard_interrupt_hook(capsys, hook_payload_path, command):
    (
        mock_project,
        patch_project,
        patch_session,
        patch_creds,
        patch_account,
        patch_type_name,
    ) = _setup_hook_test()
    patch_dumps = patch.object(json, "dumps", side_effect=KeyboardInterrupt)

    # fmt: off
    with patch_project, \
         patch_creds, \
         patch_dumps, \
         patch_account, \
         patch_type_name, \
         patch_session as mock_session:
        mock_client = mock_session.return_value.client.return_value
        main(args_in=["invoke", "hook", command, str(hook_payload_path)])
    # fmt: on

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


def _invoke_and_expect_resource(status, resource_payload_path, command, *args):
    (
        mock_project,
        patch_project,
        patch_session,
        patch_creds,
        patch_account,
    ) = _setup_resource_test()

    # fmt: off
    with patch_project, \
         patch_account, \
         patch_session as mock_session, \
            patch_creds as mock_creds:
        mock_client = mock_session.return_value.client.return_value
        mock_client.invoke.side_effect = lambda **_kwargs: {
            "Payload": StringIO(json.dumps({"status": status}))
        }
        main(args_in=["invoke", "resource", command, str(resource_payload_path), *args])
    # fmt: on
    mock_creds.assert_called()

    return mock_project, mock_client.invoke


def _invoke_and_expect_hook(status, hook_payload_path, command, *args):
    (
        mock_project,
        patch_project,
        patch_session,
        patch_creds,
        patch_account,
        patch_type_name,
    ) = _setup_hook_test()

    # fmt: off
    with patch_project, \
         patch_account, \
         patch_type_name, \
         patch_session as mock_session, \
            patch_creds as mock_creds:
        mock_client = mock_session.return_value.client.return_value
        mock_client.invoke.side_effect = lambda **_kwargs: {
            "Payload": StringIO(json.dumps({"status": status}))
        }
        main(args_in=["invoke", "hook", command, str(hook_payload_path), *args])
    # fmt: on
    mock_creds.assert_called()

    return mock_project, mock_client.invoke
