import argparse
import tempfile
from unittest import mock

from uluru.cli import main
from uluru.test import local_lambda

EXPECTED_PYTEST_ARGS = [
    "--pyargs",
    "uluru.tests.contract_tests",
    "-p",
    "no:warnings",
    "--verbose",
]


def test_test_subcommand():
    with mock.patch("uluru.test.local_lambda") as mock_lambda_command:
        test_file = tempfile.NamedTemporaryFile()
        main(args_in=["test", "local-lambda", test_file.name])

        mock_lambda_command.assert_called_once()
        args, _ = mock_lambda_command.call_args
        argparse_namespace = args[0]
        assert argparse_namespace.endpoint == "http://127.0.0.1:3001"
        assert argparse_namespace.function_name == "Handler"
        assert argparse_namespace.resource.name == test_file.name
        assert argparse_namespace.subparser_name == "test"


def test_local_lambda_command():
    with mock.patch("json.load", return_value={}), mock.patch(
        "pytest.main"
    ) as mock_pytest:
        test_file = tempfile.TemporaryFile()
        arg_namespace = argparse.Namespace(
            endpoint="http://127.0.0.1:3001",
            function_name="Handler",
            resource=test_file,
            subparser_name="test",
            test_types=None,
        )
        local_lambda(arg_namespace)
        mock_pytest.assert_called_once()
        args, _ = mock_pytest.call_args
        assert args[0] == EXPECTED_PYTEST_ARGS


def test_local_lambda_with_test_type():
    with mock.patch("json.load", return_value={}), mock.patch(
        "pytest.main"
    ) as mock_pytest:
        test_file = tempfile.NamedTemporaryFile()
        arg_namespace = argparse.Namespace(
            endpoint="http://127.0.0.1:3001",
            function_name="Handler",
            resource=test_file,
            subparser_name="test",
            test_types="TEST_TYPE",
        )
        local_lambda(arg_namespace)
        mock_pytest.assert_called_once()
        args, _ = mock_pytest.call_args
        assert args[0] == EXPECTED_PYTEST_ARGS + ["-k", "TEST_TYPE"]
