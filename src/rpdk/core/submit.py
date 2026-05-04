"""This sub command uploads the resource type to CloudFormation.

Projects can be created via the 'init' sub command.
"""
import logging
from pathlib import Path

from .exceptions import InvalidProjectError
from .package_validator import PackageValidator
from .project import Project

LOG = logging.getLogger(__name__)


def submit(args):
    # cfn submit --package <path>: skip the packaging workflow and upload the
    # pre-built zip as-is (see --package on the subparser).
    if args.package:
        _submit_existing_package(args)
        return

    project = Project()
    project.load()
    # Use CLI override opposed to config file if use-docker or no-docker switch used
    if args.use_docker or args.no_docker:
        project.settings["use_docker"] = args.use_docker
        project.settings["no_docker"] = args.no_docker
    project.submit(
        args.dry_run,
        args.endpoint_url,
        args.region,
        args.role_arn,
        args.use_role,
        args.set_default,
        args.profile,
    )


def _validate_package_flag_combinations(args):
    """Reject flag combinations that do not apply to ``--package``.

    ``--dry-run``, ``--use-docker`` and ``--no-docker`` all configure the
    packaging step. When ``--package`` is used, the zip is already built,
    so combining them is almost certainly a user mistake.

    Raises:
        InvalidProjectError: If any of the packaging-only flags are set.
    """
    conflicts = []
    if args.dry_run:
        conflicts.append("--dry-run")
    if args.use_docker:
        conflicts.append("--use-docker")
    if args.no_docker:
        conflicts.append("--no-docker")
    if conflicts:
        raise InvalidProjectError(
            f"--package cannot be combined with {', '.join(conflicts)}."
        )


def _submit_existing_package(args):
    """Upload a pre-built schema handler package without repackaging.

    The flow is:

    1. Reject flag combinations that don't make sense with ``--package``.
    2. Validate the zip's structure and read metadata out of it.
    3. Build a minimal :class:`Project` via :meth:`Project.from_package`
       (no ``.rpdk-config`` in CWD is required).
    4. Stream the zip bytes straight into ``Project._upload``.
    """
    _validate_package_flag_combinations(args)

    package_path = Path(args.package)
    metadata = PackageValidator(package_path).validate()
    project = Project.from_package(metadata)

    with open(package_path, "rb") as fileobj:
        # pylint: disable=protected-access
        project._upload(
            fileobj,
            args.endpoint_url,
            args.region,
            args.role_arn,
            args.use_role,
            args.set_default,
            args.profile,
        )


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("submit", description=__doc__, parents=parents)
    parser.set_defaults(command=submit)

    parser.add_argument(
        "--dry-run", action="store_true", help="Package the project, but do not submit."
    )
    parser.add_argument("--endpoint-url", help="CloudFormation endpoint to use.")
    parser.add_argument("--region", help="AWS Region to submit the resource type.")
    parser.add_argument(
        "--set-default",
        action="store_true",
        help="If registration is successful, set submitted version to the default.",
    )
    parser.add_argument("--profile", help="AWS profile to use.")
    parser.add_argument(
        "--package",
        "-p",
        metavar="PATH",
        help=(
            "Submit a pre-built schema handler package (zip) instead of "
            "building one from the current project. Cannot be combined with "
            "--dry-run, --use-docker, or --no-docker."
        ),
    )
    role_group = parser.add_mutually_exclusive_group()
    role_group.add_argument(
        "--role-arn",
        help="Role ARN that CloudFormation will use when invoking handlers.",
    )
    role_group.add_argument(
        "--no-role",
        action="store_false",
        dest="use_role",
        help=(
            "Register the type without an explicit execution role "
            "(Will not be able to invoke AWS APIs)."
        ),
    )

    nodocker_group = parser.add_mutually_exclusive_group()
    nodocker_group.add_argument(
        "--use-docker",
        action="store_true",
        help="""Use docker for platform-independent packaging.
            This is highly recommended unless you are experienced
            with cross-platform packaging.""",
    )
    nodocker_group.add_argument(
        "--no-docker",
        action="store_true",
        help="""Generally not recommended unless you are experienced
            with cross-platform packaging.""",
    )
