import argparse
import tempfile
from unittest import mock

import pytest

from rpdk.cli import main
from rpdk.test import local_lambda

EXPECTED_PYTEST_ARGS = [
    "--pyargs",
    "rpdk.contract.contract_tests",
    "-p",
    "no:warnings",
    "--verbose",
]


def test_test_command_help(capsys):
    # also mock other transports here
    with mock.patch("rpdk.test.local_lambda", autospec=True) as mock_local_lambda:
        main(args_in=["test"])
    out, _ = capsys.readouterr()
    assert "--help" in out
    mock_local_lambda.assert_not_called()


def test_test_command_local_lambda_help(capsys):
    with mock.patch("rpdk.test.local_lambda", autospec=True) as mock_local_lambda:
        with pytest.raises(SystemExit):
            main(args_in=["test", "local-lambda"])
    _, err = capsys.readouterr()
    assert "usage" in err
    mock_local_lambda.assert_not_called()


def test_test_command_args():
    with mock.patch("rpdk.test.local_lambda", autospec=True) as mock_lambda_command:
        test_resource_file = tempfile.NamedTemporaryFile()
        test_resource_def_file = tempfile.NamedTemporaryFile()
        main(
            args_in=[
                "test",
                "local-lambda",
                test_resource_file.name,
                test_resource_def_file.name,
            ]
        )

    mock_lambda_command.assert_called_once()
    args, _ = mock_lambda_command.call_args
    argparse_namespace = args[0]
    assert argparse_namespace.endpoint == "http://127.0.0.1:3001"
    assert argparse_namespace.function_name == "Handler"
    assert argparse_namespace.resource_file.name == test_resource_file.name
    assert argparse_namespace.resource_def_file.name == test_resource_def_file.name
    assert argparse_namespace.subparser_name == "test"


def test_local_lambda_command():
    with tempfile.TemporaryFile() as test_file:
        arg_namespace = argparse.Namespace(
            endpoint="http://127.0.0.1:3001",
            function_name="Handler",
            resource_file=test_file,
            resource_def_file=test_file,
            subparser_name="test",
            test_types=None,
        )
        with mock.patch("json.load", return_value={}, autospec=True), mock.patch(
            "pytest.main"
        ) as mock_pytest:
            local_lambda(arg_namespace)
    mock_pytest.assert_called_once()
    args, _ = mock_pytest.call_args
    assert args[0] == EXPECTED_PYTEST_ARGS


def test_local_lambda_with_test_type():
    with tempfile.TemporaryFile() as test_file:
        arg_namespace = argparse.Namespace(
            endpoint="http://127.0.0.1:3001",
            function_name="Handler",
            resource_file=test_file,
            resource_def_file=test_file,
            subparser_name="test",
            test_types="TEST_TYPE",
        )
        with mock.patch("json.load", return_value={}, autospec=True), mock.patch(
            "pytest.main", autospec=True
        ) as mock_pytest:
            local_lambda(arg_namespace)
    mock_pytest.assert_called_once()
    args, _ = mock_pytest.call_args
    assert args[0] == EXPECTED_PYTEST_ARGS + ["-k", "TEST_TYPE"]
