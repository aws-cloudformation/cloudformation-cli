"""This sub command submits the completed resource provider to the specified
AWS account."""
import time


def submit(args):
    print("Submitting your resource provider handlers to your AWS account...")
    time.sleep(4)
    print("Submission SUCCESS")


def submit_setup_subparser(subparsers):
    parser = subparsers.add_parser(
        'submit',
        description=__doc__)
    parser.set_defaults(command=submit)
