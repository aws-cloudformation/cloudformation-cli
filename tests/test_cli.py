import logging

from rpdk.cli import main, setup_logging

DEBUG_MSG = "DQCDVI"
INFO_MSG = "TDDJOG"
WARNING_MSG = "XLTCQQ"


def setup_logging_do_logging_and_capture(capsys, verbosity):
    setup_logging(verbosity)
    logger = logging.getLogger("rpdk")
    logger.debug(DEBUG_MSG)
    logger.info(INFO_MSG)
    logger.warning(WARNING_MSG)
    out, _ = capsys.readouterr()
    return out


def test_setup_logging_console_zero_verbosity(capsys):
    out = setup_logging_do_logging_and_capture(capsys, 0)
    assert WARNING_MSG in out
    assert INFO_MSG not in out
    assert DEBUG_MSG not in out


def test_setup_logging_console_one_verbosity(capsys):
    out = setup_logging_do_logging_and_capture(capsys, 1)
    assert WARNING_MSG in out
    assert INFO_MSG in out
    assert DEBUG_MSG not in out


def test_setup_logging_console_two_verbosity(capsys):
    out = setup_logging_do_logging_and_capture(capsys, 2)
    assert WARNING_MSG in out
    assert INFO_MSG in out
    assert DEBUG_MSG in out


def test_main_no_args_prints_help(capsys):
    main(args_in=[])
    out, _ = capsys.readouterr()
    assert "--help" in out
