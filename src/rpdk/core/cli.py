"""This tool provides support for creating CloudFormation resource providers.
"""
import argparse
import logging
import sys
import time
from logging.config import dictConfig

from colorama import colorama_text

from .__init__ import __version__
from .build_image import setup_subparser as build_image_setup_subparser
from .data_loaders import resource_yaml
from .exceptions import DownstreamError, SysExitRecommendedError
from .generate import setup_subparser as generate_setup_subparser
from .init import setup_subparser as init_setup_subparser
from .invoke import setup_subparser as invoke_setup_subparser
from .submit import setup_subparser as submit_setup_subparser
from .test import setup_subparser as test_setup_subparser
from .validate import setup_subparser as validate_setup_subparser

EXIT_UNHANDLED_EXCEPTION = 127


class UTCFormatter(logging.Formatter):
    converter = time.gmtime


def setup_logging(verbosity):
    """Configure logging with a variable verbosity level (0, 1, 2)."""
    if verbosity > 1:
        level = logging.DEBUG
    elif verbosity > 0:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging_config = resource_yaml(__name__, "data/logging.yaml")
    logging_config["handlers"]["console"]["level"] = level
    dictConfig(logging_config)


def unittest_patch_setup_subparser(_subparsers, _parents):
    pass


def main(args_in=None):  # pylint: disable=too-many-statements
    """The entry point for the CLI."""
    log = None
    try:
        # see docstring of this file
        parser = argparse.ArgumentParser(description=__doc__)
        # the default command just prints the help message
        # subparsers should set their own default commands
        # also need to set verbose here because now it only gets set if a
        # subcommand is run (which is okay, the help doesn't need it)

        def no_command(args):
            if args.version:
                print("cfn", __version__)
            else:
                parser.print_help()

        parser.set_defaults(command=no_command, verbose=0)
        parser.add_argument(
            "--version",
            action="store_true",
            help="Show the executable version and exit.",
        )

        base_subparser = argparse.ArgumentParser(add_help=False)
        # shared arguments
        base_subparser.add_argument(
            "-v",
            "--verbose",
            action="count",
            default=0,
            help="Increase the output verbosity. Can be specified multiple times.",
        )
        parents = [base_subparser]

        subparsers = parser.add_subparsers(dest="subparser_name")
        init_setup_subparser(subparsers, parents)
        validate_setup_subparser(subparsers, parents)
        submit_setup_subparser(subparsers, parents)
        generate_setup_subparser(subparsers, parents)
        test_setup_subparser(subparsers, parents)
        invoke_setup_subparser(subparsers, parents)
        unittest_patch_setup_subparser(subparsers, parents)
        build_image_setup_subparser(subparsers, parents)
        args = parser.parse_args(args=args_in)

        setup_logging(args.verbose)

        log = logging.getLogger(__name__)
        log.debug("Logging set up successfully")
        log.debug("Running %s: %s", args.subparser_name, args)

        with colorama_text():
            args.command(args)

        log.debug("Finished %s", args.subparser_name)
    except SysExitRecommendedError as e:
        # This is to unify exit messages, and avoid throwing SystemExit in
        # library code, which is hard to catch for consumers. (There are still
        # some cases where it makes sense for the commands to raise SystemExit.)
        log.debug("Caught exit recommendation", exc_info=e)
        log.critical(str(e))
        # pylint: disable=W0707
        raise SystemExit(1)
    except DownstreamError as e:
        # For these operations, we don't want to swallow the exception
        log.debug("Caught downstream error", exc_info=e)
        print("=== Caught downstream error ===", file=sys.stderr)
        print(str(e.__cause__), file=sys.stderr)
        print("---", file=sys.stderr)
        print(
            "If debugging indicates this is a possible error with this program,",
            file=sys.stderr,
        )
        print(
            "please report the issue to the team and include the log file 'rpdk.log'.",
            file=sys.stderr,
        )
        print(
            "Issue tracker: "
            "https://github.com/aws-cloudformation/aws-cloudformation-rpdk/issues",
            file=sys.stderr,
        )
        # pylint: disable=W0707
        raise SystemExit(2)
    except Exception:  # pylint: disable=broad-except
        print("=== Unhandled exception ===", file=sys.stderr)
        print("Please report this issue to the team.", file=sys.stderr)
        print(
            "Issue tracker: "
            "https://github.com/aws-cloudformation/aws-cloudformation-rpdk/issues",
            file=sys.stderr,
        )

        if log:
            print("Please include the log file 'rpdk.log'", file=sys.stderr)
            log.debug("Unhandled exception", exc_info=True)
        else:
            print("Please include this information:", file=sys.stderr)
            import traceback  # pylint: disable=import-outside-toplevel

            traceback.print_exc()
        # pylint: disable=W0707
        raise SystemExit(EXIT_UNHANDLED_EXCEPTION)
