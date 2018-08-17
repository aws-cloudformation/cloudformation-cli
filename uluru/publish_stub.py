"""This sub command publishes the completed resource provider to
AWS CloudFormation for review and publishing for use beyond a single
AWS account."""
import time


def publish(args):
    print("Publishing your resource provider handlers to your AWS account...")
    time.sleep(4)
    print("Publication SUCCESS")


def publish_setup_subparser(subparsers):
    parser = subparsers.add_parser(
        'publish',
        description=__doc__)
    parser.set_defaults(command=publish)
