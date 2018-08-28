"""This sub command tests the completed resource provider with both unit and
integration tests."""
import time


def test(args):
    # THIS IS A MOCKUP.
    print("Running tests on your resource package...")
    time.sleep(1)
    print("CreateHandler unit tests PASSED...")
    time.sleep(1)
    print("DeleteHandler unit tests PASSED...")
    time.sleep(10)
    print("UpdateHandler unit tests PASSED...")
    time.sleep(1)
    print("ReadHandler unit tests PASSED...")
    time.sleep(1)
    print("ListHandler unit tests PASSED...")
    time.sleep(3)
    print("Integration tests PASSED...")
    print("Test SUCCESS")


def test_setup_subparser(subparsers):
    parser = subparsers.add_parser("test", description=__doc__)
    parser.set_defaults(command=test)
