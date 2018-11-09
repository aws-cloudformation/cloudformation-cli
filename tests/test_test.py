import argparse
from contextlib import contextmanager
from tempfile import NamedTemporaryFile, TemporaryFile
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from rpdk.cli import main
from rpdk.test import invoke_pytest, local_lambda, setup_subparser, temporary_ini_file

RANDOM_INI = "pytest_SOYPKR.ini"
EXPECTED_PYTEST_ARGS = ["--pyargs", "rpdk.contract.suite", "-c", RANDOM_INI]


@contextmanager
def mock_temporary_ini_file():
    yield RANDOM_INI


def test_test_command_help(capsys):
    # also mock other transports here
    with patch("rpdk.test.local_lambda", autospec=True) as mock_local_lambda:
        main(args_in=["test"])
    out, _ = capsys.readouterr()
    assert "--help" in out
    mock_local_lambda.assert_not_called()


def test_test_command_local_lambda_help(capsys):
    with patch("rpdk.test.local_lambda", autospec=True) as mock_local_lambda:
        with pytest.raises(SystemExit):
            main(args_in=["test", "local-lambda"])
    _, err = capsys.readouterr()
    assert "usage" in err
    mock_local_lambda.assert_not_called()


def test_test_command_args():
    with patch("rpdk.test.local_lambda", autospec=True) as mock_lambda_command:
        test_resource_file = NamedTemporaryFile()
        test_updated_resource_file = NamedTemporaryFile()
        test_resource_def_file = NamedTemporaryFile()
        main(
            args_in=[
                "test",
                "local-lambda",
                test_resource_file.name,
                test_updated_resource_file.name,
                test_resource_def_file.name,
            ]
        )

    mock_lambda_command.assert_called_once()
    args, _ = mock_lambda_command.call_args
    argparse_namespace = args[0]
    assert argparse_namespace.endpoint == "http://127.0.0.1:3001"
    assert argparse_namespace.function_name == "Handler"
    assert argparse_namespace.resource_file.name == test_resource_file.name
    assert (
        argparse_namespace.updated_resource_file.name == test_updated_resource_file.name
    )
    assert argparse_namespace.resource_def_file.name == test_resource_def_file.name
    assert argparse_namespace.subparser_name == "test"


def test_invoke_pytest():
    arg_namespace = argparse.Namespace(
        endpoint="http://127.0.0.1:3001",
        function_name="Handler",
        resource_file=None,
        updated_resource_file=None,
        resource_def_file=None,
        subparser_name="test",
        test_types=None,
        collect_only=False,
    )
    mock_init = patch(
        "rpdk.test.temporary_ini_file", side_effect=mock_temporary_ini_file
    )
    mock_json = patch("json.load", return_value={}, autospec=True)
    with mock_json, mock_init, patch("pytest.main") as mock_pytest:
        invoke_pytest(None, arg_namespace)
    args, kwargs = mock_pytest.call_args
    assert len(args) == 1
    assert args[0] == EXPECTED_PYTEST_ARGS
    assert kwargs.keys() == {"plugins"}


def test_invoke_pytest_with_test_type():
    arg_namespace = argparse.Namespace(
        endpoint="http://127.0.0.1:3001",
        function_name="Handler",
        resource_file=None,
        updated_resource_file=None,
        resource_def_file=None,
        subparser_name="test",
        test_types="TEST_TYPES",
        collect_only=False,
    )
    mock_init = patch(
        "rpdk.test.temporary_ini_file", side_effect=mock_temporary_ini_file
    )
    mock_json = patch("json.load", return_value={}, autospec=True)
    with mock_json, mock_init, patch("pytest.main") as mock_pytest:
        invoke_pytest(None, arg_namespace)
    args, kwargs = mock_pytest.call_args
    assert len(args) == 1
    assert args[0] == EXPECTED_PYTEST_ARGS + ["-k", "TEST_TYPES"]
    assert kwargs.keys() == {"plugins"}


def test_local_lambda_command():
    with TemporaryFile() as test_file, patch(
        "rpdk.contract.transports.LocalLambdaTransport.__call__"
    ), patch("rpdk.test.invoke_pytest") as mock_invoke_pytest:
        arg_namespace = argparse.Namespace(
            endpoint="http://127.0.0.1:3001",
            function_name="Handler",
            resource_file=test_file,
            updated_resource_file=test_file,
            resource_def_file=test_file,
            subparser_name="test",
            test_types=None,
        )
        local_lambda(arg_namespace)
    mock_invoke_pytest.assert_called_once()
    args = mock_invoke_pytest.call_args[0]
    assert args[0].endpoint == "http://127.0.0.1:3001"
    assert args[0].function_name == "Handler"
    assert args[1] == arg_namespace


def test_local_lambda_fail_fast_endpoint():
    arg_namespace = argparse.Namespace(
        endpoint="http://127.0.0.1:3001", function_name="Handler"
    )

    mock_transport_call = patch(
        "rpdk.contract.transports.LocalLambdaTransport.__call__",
        new=Mock(
            side_effect=EndpointConnectionError(endpoint_url="http://127.0.0.1:3001")
        ),
    )
    with mock_transport_call, patch("rpdk.test.invoke_pytest") as mock_pytest:
        local_lambda(arg_namespace)
    mock_pytest.assert_not_called()


def test_local_lambda_fail_fast_function_name():
    arg_namespace = argparse.Namespace(
        endpoint="http://127.0.0.1:3001", function_name="Handler"
    )
    error_message = {"Error": {"Message": "Function not found"}}
    mock_transport_call = Mock(side_effect=ClientError(error_message, ""))
    with patch("rpdk.test.invoke_pytest") as mock_pytest, patch(
        "rpdk.contract.transports.LocalLambdaTransport.__call__",
        new=mock_transport_call,
    ):
        local_lambda(arg_namespace)
    mock_pytest.assert_not_called()


def test_temporary_ini_file():
    with temporary_ini_file() as path:
        with open(path, "r", encoding="utf-8") as f:
            assert "[pytest]" in f.read()


def mock_transport_command(args):
    transport = Mock()
    invoke_pytest(transport, args)


def patched_setup_subparser(subparsers, parents):
    test_parsers, pytest_parents = setup_subparser(subparsers, parents)
    mock_parser = test_parsers.add_parser("mock-transport", parents=pytest_parents)
    mock_parser.set_defaults(command=mock_transport_command)


def test_e2e_test_command(capsys):
    with patch(
        "rpdk.cli.test_setup_subparser", side_effect=patched_setup_subparser
    ), NamedTemporaryFile(mode="w+", encoding="utf8", delete=False) as temp:
        temp.write("{}")
        temp.close()
        main(
            [
                "test",
                "mock-transport",
                temp.name,
                temp.name,
                temp.name,
                "--collect-only",
            ]
        )
    assert "collected" in capsys.readouterr()[0]
