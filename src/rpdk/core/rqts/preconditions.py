"""Precondition checks for the RQTS (CTv2 local) contract test runner.

``cfn test --v2`` requires several runtime and project prerequisites before the
RQTS container can run: a working Docker runtime, a Java project, a built
artifact package, and valid AWS credentials and region.

The DirectJar handler mode loads the handler JAR directly into the executor
JVM, so there is no SAM Local handler endpoint to probe and no separate input
resolution: inputs are packaged inside the artifact zip and read from there by
the executor. It also means a non-Java project has no artifact the executor can
invoke, which is why the language is checked up front.

Each check in this module is independent and side-effect-free with respect to
the others. A check appends a single human-readable message on failure and
NEVER raises, so the caller (``RqtsRunner``) can aggregate every unmet
precondition into one error rather than failing on the first problem
(Requirement 3.7). ``check_preconditions`` returns the aggregated list of
failure messages; an empty list means all preconditions are met.
"""

import logging
import shutil
import subprocess  # nosec B404

from ..boto_helpers import create_sdk_session, get_service_endpoint
from .constants import JAVA_LANGUAGE

LOG = logging.getLogger(__name__)

# Bounded timeout (seconds) for the Docker daemon ping so a hung daemon cannot
# stall the precondition phase.
_DOCKER_INFO_TIMEOUT_SECONDS = 10


def _check_docker():
    """Return a failure message if Docker is unavailable, else ``None``.

    Docker is available only when the ``docker`` CLI is present on PATH AND the
    Docker daemon is reachable (probed with ``docker info``) (Requirement 3.2).
    """
    if shutil.which("docker") is None:
        return (
            "Docker is required and must be running: the 'docker' CLI was not "
            "found on PATH."
        )

    try:
        result = subprocess.run(  # nosec B603, B607
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=_DOCKER_INFO_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as e:
        LOG.debug("Docker daemon ping failed", exc_info=e)
        return (
            "Docker is required and must be running: the Docker daemon could "
            "not be reached."
        )

    if result.returncode != 0:
        return (
            "Docker is required and must be running: the Docker daemon could "
            "not be reached."
        )

    return None


def _check_language(project):
    """Return a failure message unless the project is a Java project.

    DirectJar loads a handler JAR directly into the executor JVM, so only the
    Java language plugin produces a usable artifact. ``project.language`` is that
    plugin's ``rpdk.v1.languages`` entry point name, as recorded in
    ``.rpdk-config``.
    """
    if project.language != JAVA_LANGUAGE:
        return (
            "the RQTS local test runner supports Java projects only; this "
            f"project's language is '{project.language}'."
        )
    return None


def _check_artifact(project):
    """Return a failure message if the built artifact package is missing.

    Mirrors ``Project._get_zip_file_path()``: the package lives at
    ``project.root / f"{project.hypenated_name}.zip"`` (Requirement 3.3).
    """
    artifact_name = f"{project.hypenated_name}.zip"
    artifact_path = project.root / artifact_name
    if not artifact_path.is_file():
        return (
            f"artifact package '{artifact_name}' not found; build the project " "first."
        )
    return None


def _check_credentials(args):
    """Return a failure message if AWS credentials or region are unavailable.

    ``create_sdk_session`` raises when the region or credentials are missing, but
    it makes no network call, so it cannot tell whether the credentials still
    work. ``sts:GetCallerIdentity`` verifies them, which matters because
    ``get_temporary_credentials`` passes an already-temporary session token
    through unchanged: without this, expired credentials would reach the
    container and fail there instead of here (Requirement 3.5).
    """
    try:
        session = create_sdk_session(args.region, args.profile)
        session.client(
            "sts",
            endpoint_url=get_service_endpoint("sts", session.region_name),
            region_name=session.region_name,
        ).get_caller_identity()
    except Exception as e:  # pylint: disable=broad-except
        LOG.debug("AWS credentials could not be verified", exc_info=e)
        return (
            "valid AWS credentials and a region are required; they could not be "
            "verified and may be expired."
        )
    return None


def check_preconditions(args, project):
    """Verify all ``cfn test --v2`` preconditions and aggregate any failures.

    Runs each independent precondition check and collects the human-readable
    failure message from every unmet one. No check raises; the caller turns a
    non-empty list into a single ``SysExitRecommendedError`` (Requirements 3.1,
    3.7).

    :param args: parsed CLI arguments (uses ``args.region`` and ``args.profile``)
    :param project: loaded ``rpdk.core.project.Project``
    :returns: list of failure messages; empty means all preconditions are met
    """
    failures = []
    for message in (
        _check_docker(),
        _check_language(project),
        _check_artifact(project),
        _check_credentials(args),
    ):
        if message is not None:
            failures.append(message)
    return failures
