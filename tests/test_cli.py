import logging
from unittest.mock import patch

import pytest

from rpdk.core import __version__
from rpdk.core.cli import EXIT_UNHANDLED_EXCEPTION, main, setup_logging
from rpdk.core.exceptions import DownstreamError, SysExitRecommendedError

from .utils import chdir

DEBUG_MSG = "DQCDVI"
INFO_MSG = "TDDJOG"
WARNING_MSG = "XLTCQQ"
ERROR_MSG = "PXVSNS"


def setup_logging_do_logging_and_capture(name, capsys, verbosity):
    setup_logging(verbosity)
    logger = logging.getLogger(name)
    logger.debug(DEBUG_MSG)
    logger.info(INFO_MSG)
    logger.warning(WARNING_MSG)
    logger.error(ERROR_MSG)
    return capsys.readouterr()


def assert_all_messages_logged(cwd):
    with open(cwd.join("rpdk.log"), "r", encoding="utf-8") as f:
        log = f.read()
    assert ERROR_MSG in log
    assert WARNING_MSG in log
    assert INFO_MSG in log
    assert DEBUG_MSG in log


def test_setup_logging_console_zero_verbosity(tmpdir, capsys):
    with chdir(tmpdir) as cwd:
        out, err = setup_logging_do_logging_and_capture("rpdk", capsys, 0)
    assert not err
    assert ERROR_MSG in out
    assert WARNING_MSG in out
    assert INFO_MSG not in out
    assert DEBUG_MSG not in out

    assert_all_messages_logged(cwd)


def test_setup_logging_console_one_verbosity(tmpdir, capsys):
    with chdir(tmpdir) as cwd:
        out, err = setup_logging_do_logging_and_capture("rpdk", capsys, 1)
    assert not err
    assert ERROR_MSG in out
    assert WARNING_MSG in out
    assert INFO_MSG in out
    assert DEBUG_MSG not in out

    assert_all_messages_logged(cwd)


def test_setup_logging_console_two_verbosity(tmpdir, capsys):
    with chdir(tmpdir) as cwd:
        out, err = setup_logging_do_logging_and_capture("rpdk", capsys, 2)
    assert not err
    assert ERROR_MSG in out
    assert WARNING_MSG in out
    assert INFO_MSG in out
    assert DEBUG_MSG in out

    assert_all_messages_logged(cwd)


def test_main_no_args_prints_help(capsys):
    main(args_in=[])
    out, err = capsys.readouterr()
    assert not err
    assert "--help" in out


def test_main_version_arg_prints_version(capsys):
    main(args_in=["--version"])
    out, err = capsys.readouterr()
    assert not err
    assert __version__ in out


@pytest.mark.parametrize("verbosity", (0, 1, 2))
def test_setup_logging_console_overrides(tmpdir, capsys, verbosity):
    with chdir(tmpdir) as cwd:
        out, err = setup_logging_do_logging_and_capture("boto3", capsys, verbosity)
    assert not err
    assert ERROR_MSG in out
    assert WARNING_MSG not in out
    assert INFO_MSG not in out
    assert DEBUG_MSG not in out

    with open(cwd.join("rpdk.log"), "r", encoding="utf-8") as f:
        log = f.read()
    assert ERROR_MSG in log
    assert WARNING_MSG not in log
    assert INFO_MSG not in log
    assert DEBUG_MSG not in log


def test_main_unhandled_exception_before_logging(capsys):
    with patch(
        "rpdk.core.cli.unittest_patch_setup_subparser",
        autospec=True,
        side_effect=Exception,
    ) as mock_hook:
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=[])
    assert excinfo.value.code == EXIT_UNHANDLED_EXCEPTION
    mock_hook.assert_called_once()
    out, err = capsys.readouterr()
    assert not out
    assert "Unhandled exception" in err
    assert "Traceback" in err
    assert "rpdk.log" not in err


def test_main_unhandled_exception_after_logging(capsys):
    def raise_exception(_args):
        raise Exception

    def setup_subparser(subparsers, parents):
        parser = subparsers.add_parser("fail", parents=parents)
        parser.set_defaults(command=raise_exception)

    with patch(
        "rpdk.core.cli.unittest_patch_setup_subparser",
        autospec=True,
        side_effect=setup_subparser,
    ) as mock_hook:
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=["fail"])
    assert excinfo.value.code == EXIT_UNHANDLED_EXCEPTION
    mock_hook.assert_called_once()
    out, err = capsys.readouterr()
    assert not out
    assert "Unhandled exception" in err
    assert "Traceback" not in err
    assert "rpdk.log" in err
    assert "github.com" in err


def test_main_sysexit_exception_after_logging(capsys):
    def raise_exception(_args):
        raise SysExitRecommendedError(ERROR_MSG)

    def setup_subparser(subparsers, parents):
        parser = subparsers.add_parser("fail", parents=parents)
        parser.set_defaults(command=raise_exception)

    with patch(
        "rpdk.core.cli.unittest_patch_setup_subparser",
        autospec=True,
        side_effect=setup_subparser,
    ) as mock_hook:
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=["fail"])
    assert excinfo.value.code == 1
    mock_hook.assert_called_once()
    out, err = capsys.readouterr()
    assert ERROR_MSG in out
    assert not err


def test_main_downstream_wrapped_exception_after_logging(capsys):
    def raise_exception(_args):
        raise DownstreamError("ignored") from Exception(ERROR_MSG)

    def setup_subparser(subparsers, parents):
        parser = subparsers.add_parser("fail", parents=parents)
        parser.set_defaults(command=raise_exception)

    with patch(
        "rpdk.core.cli.unittest_patch_setup_subparser",
        autospec=True,
        side_effect=setup_subparser,
    ) as mock_hook:
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=["fail"])
    assert excinfo.value.code == 2
    mock_hook.assert_called_once()
    out, err = capsys.readouterr()
    assert not out
    assert ERROR_MSG in err
    assert "Traceback" not in err
    assert "rpdk.log" in err
    assert "github.com" in err
