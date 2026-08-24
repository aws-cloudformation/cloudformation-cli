# have to skip B404, subprocess is required to drive the local Docker CLI
# have to skip B603, docker is invoked with a fixed, non-shell argv
"""RQTS (CTv2 local) contract test runner.

This module drives the ``docker run`` step of ``cfn test --v2`` and maps the
container's exit code onto the CLI's exit-code contract:

* :class:`RqtsRunner` orchestrates the full ``--v2`` pipeline: it guards the
  project artifact type, aggregates and enforces preconditions, mints temporary
  AWS credentials, resolves and ensures the RQTS image, builds the ``docker
  run`` argv for the executor's DirectJar handler mode, runs the container, and
  maps its exit code. Any failure raises
  :class:`~rpdk.core.exceptions.SysExitRecommendedError`.
* :func:`run_container` spawns the ``docker run`` process, streams its
  stdout/stderr to the terminal live (as produced, without buffering to
  completion), and returns the container's exit code. A failure to even start
  the container is surfaced as a
  :class:`~rpdk.core.exceptions.SysExitRecommendedError`.
* :func:`map_exit_code` turns that exit code into the CLI's contract: ``0``
  reports a pass and returns; any non-zero code raises
  :class:`~rpdk.core.exceptions.SysExitRecommendedError`, which ``cli.py``
  already maps to ``SystemExit(1)``. It defers the human-readable pass/fail
  summary to :func:`report_result` so the summary and the exit-code mapping
  stay single-sourced.
* :func:`report_result` renders the concise overall pass/fail summary,
  consistent with the existing pytest-based ``cfn test`` reporting. The
  per-scenario/test outcomes themselves are streamed live by
  :func:`run_container`, so this summary does not re-parse or duplicate them.

The DirectJar handler mode loads the handler JAR directly into the executor
JVM, so there is no handler endpoint to probe and no host networking to
configure. Docker is driven through the ``docker`` CLI via :mod:`subprocess`.
The child inherits the parent's stdout/stderr so RQTS results appear live in
the developer's terminal exactly as the executor emits them.
"""
import logging
import os
import subprocess  # nosec B404
from pathlib import Path

from rpdk.core.exceptions import SysExitRecommendedError

from ..boto_helpers import BOTO_CRED_KEYS, create_sdk_session, get_temporary_credentials
from ..project import ARTIFACT_TYPE_HOOK, ARTIFACT_TYPE_RESOURCE
from .argv import build_container_env, build_docker_argv
from .image import ensure_image, resolve_image
from .preconditions import check_preconditions

LOG = logging.getLogger(__name__)

# Host-side directory (under the project root, i.e. under the bind mount) that
# the executor writes its output to. Created before the container runs so the
# bind-mounted output path exists on the host.
HOST_OUTPUT_DIRNAME = "rqts-output"

# Overall summary lines for a completed RQTS run. Phrasing is kept consistent
# with the existing pytest-based ``cfn test`` reporting, whose failure path
# raises ``SysExitRecommendedError("One or more contract tests failed")`` in
# ``test.invoke_test``; the RQTS variants name the runner explicitly. The
# container streams the per-scenario/test outcomes live (Requirement 6.2), so
# these are deliberately concise overall summaries (Requirement 6.1).
# B105 false positive: a log summary string, not a password (bandit matches
# the "PASS" in the variable name).
PASS_SUMMARY = "RQTS contract tests passed"  # nosec B105
FAIL_SUMMARY = "One or more RQTS contract tests failed"


def run_container(argv, env=None):
    """Spawn ``docker run`` and stream its output live, returning the exit code.

    The child process inherits the parent's stdout/stderr, so the RQTS
    executor's output is streamed to the terminal as it is produced rather than
    buffered until the process completes (Requirement 5.1). This function blocks
    until the container exits and returns its exit code.

    Credential values reach docker exclusively through ``env`` (merged over the
    ambient environment): the argv's ``-e`` flags are name-only, so the command
    line is safe to log and never carries secrets.

    :param list argv: the full ``docker run`` argv (as built by
        :func:`rpdk.core.rqts.argv.build_docker_argv`)
    :param env: optional mapping of extra environment variables (for example
        from :func:`rpdk.core.rqts.argv.build_container_env`) merged over
        ``os.environ`` for the docker client process
    :return: the container's exit code
    :rtype: int
    :raises SysExitRecommendedError: if the container process cannot be spawned
    """
    LOG.debug("Running RQTS container: %s", " ".join(argv))
    process_env = {**os.environ, **env} if env else None
    try:
        # stdout/stderr default to None, so the child inherits the parent's
        # terminal and streams output live without buffering (Requirement 5.1).
        with subprocess.Popen(argv, env=process_env) as process:  # nosec B603
            return process.wait()
    except OSError as err:
        LOG.debug("Failed to start the RQTS container", exc_info=err)
        raise SysExitRecommendedError(
            f"the RQTS container could not be started: {err}"
        ) from err


def report_result(code):
    """Surface the overall pass/fail summary for a completed RQTS run.

    The RQTS container already streams its per-scenario/test outcomes to the
    terminal live via :func:`run_container` (Requirements 5.1, 6.2); this helper
    adds only the concise overall summary that mirrors the existing
    pytest-based ``cfn test`` reporting (Requirement 6.1), without re-parsing or
    duplicating the streamed output. A ``0`` code logs an informational pass
    summary; any non-zero code raises :class:`SysExitRecommendedError` whose
    message names the RQTS runner, consistent with the existing "One or more
    contract tests failed" phrasing used by the pytest path.

    This helper only renders the summary; the exit-code interpretation itself is
    owned by :func:`map_exit_code`, which calls this helper so the summary and
    the exit-code mapping stay single-sourced (Requirement 6.3).

    :param int code: the container's exit code
    :raises SysExitRecommendedError: if ``code`` is non-zero
    """
    if code == 0:
        LOG.info(PASS_SUMMARY)
        return
    raise SysExitRecommendedError(FAIL_SUMMARY)


def map_exit_code(code):
    """Map the RQTS container exit code onto the CLI's exit-code contract.

    A ``0`` exit code means every RQTS contract test passed: an informational
    summary is logged and the function returns normally so the CLI exits ``0``
    (Requirements 5.2, 6.1). Any non-zero exit code means one or more contract
    tests failed and raises :class:`SysExitRecommendedError`, which ``cli.py``
    maps to ``SystemExit(1)`` (Requirements 5.3, 6.3).

    The pass/fail summary is delegated to :func:`report_result` so that the
    reporting and the exit-code mapping remain single-sourced; this function is
    the exit-code contract entry point invoked by :meth:`RqtsRunner.run`.

    :param int code: the container's exit code
    :raises SysExitRecommendedError: if ``code`` is non-zero
    """
    report_result(code)


class RqtsRunner:
    """Orchestrates the ``cfn test --v2`` RQTS pipeline.

    A single instance owns the parsed CLI ``args`` and the loaded
    :class:`~rpdk.core.project.Project` and drives the fixed pipeline in
    :meth:`run`: artifact-type guard, precondition aggregation, credential
    minting, image resolve/ensure, ``docker run`` argv construction (for the
    executor's DirectJar handler mode), container execution, and exit-code
    mapping.

    Module projects are short-circuited upstream in ``test()`` before the runner
    is constructed, so this class only handles resource (the supported case),
    hook, and indeterminate artifact types.
    """

    def __init__(self, args, project):
        """Store the parsed CLI arguments and the loaded project.

        :param args: parsed CLI arguments (an argparse ``Namespace``). The
            runner reads ``region``, ``profile``, ``role_arn``,
            ``source_account``, ``source_arn`` and ``rqts_image``.
        :param project: the loaded :class:`~rpdk.core.project.Project`.
        """
        self.args = args
        self.project = project

    def _guard_artifact_type(self):
        """Fail fast unless the project is a supported resource type.

        Hook projects are unsupported by the RQTS local runner (Requirement
        7.2); any artifact type that is neither a resource nor a hook is treated
        as indeterminate (Requirement 7.5). Module projects are handled upstream
        in ``test()`` and never reach this method.

        :raises SysExitRecommendedError: for hook or indeterminate artifact
            types
        """
        artifact_type = self.project.artifact_type
        if artifact_type == ARTIFACT_TYPE_HOOK:
            raise SysExitRecommendedError(
                "the RQTS local test runner supports resource types only"
            )
        if artifact_type != ARTIFACT_TYPE_RESOURCE:
            raise SysExitRecommendedError(
                "could not determine the project artifact type"
            )

    def _mint_credentials(self):
        """Mint temporary AWS credentials for the container to use.

        Reuses the exact ``boto_helpers`` pattern used by the contract-test
        path: create a session from the effective region/profile, then request
        temporary credentials (assuming ``--role-arn`` when supplied) with the
        confused-deputy ``--source-account`` / ``--source-arn`` headers
        (Requirement 3.5). ``BOTO_CRED_KEYS`` is used so the returned mapping's
        keys match what :func:`rpdk.core.rqts.argv.build_docker_argv` expects.

        :return: a mapping of temporary credentials keyed by ``BOTO_CRED_KEYS``
        :rtype: dict
        """
        session = create_sdk_session(self.args.region, self.args.profile)
        return get_temporary_credentials(
            session,
            BOTO_CRED_KEYS,
            self.args.role_arn,
            headers={
                "account_id": self.args.source_account,
                "source_arn": self.args.source_arn,
            },
        )

    def run(self):
        """Orchestrate the full ``--v2`` pipeline.

        Raises :class:`~rpdk.core.exceptions.SysExitRecommendedError` on any
        failure (guard, preconditions, image pull, container start, or a
        non-zero container exit code); returns normally when every RQTS contract
        test passes.
        """
        self._guard_artifact_type()

        failures = check_preconditions(self.args, self.project)
        if failures:
            raise SysExitRecommendedError(
                "cannot run 'cfn test --v2'; the following preconditions were "
                "not met:\n" + "\n".join(f"  - {failure}" for failure in failures)
            )

        creds = self._mint_credentials()

        image_ref = resolve_image(self.args)
        ensure_image(image_ref)

        # Ensure the host-side output directory (under the bind mount) exists so
        # the container's -o path is present when docker mounts it.
        output_dir = Path(self.project.root) / HOST_OUTPUT_DIRNAME
        output_dir.mkdir(parents=True, exist_ok=True)

        # The argv is credential-free (name-only -e flags), so logging the full
        # command line at DEBUG (Req 4.10) cannot leak secrets; the values
        # travel only through the docker client process environment.
        argv = build_docker_argv(
            image_ref,
            self.project,
            self.args.region,
        )
        LOG.debug("RQTS docker command: %s", " ".join(argv))

        container_env = build_container_env(creds, self.args.region)
        exit_code = run_container(argv, env=container_env)
        map_exit_code(exit_code)
