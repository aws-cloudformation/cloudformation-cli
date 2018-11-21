import logging

import pytest

from rpdk.cli import main, setup_logging

from .test_init import chdir

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
    out, _ = capsys.readouterr()
    assert "--help" in out


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
