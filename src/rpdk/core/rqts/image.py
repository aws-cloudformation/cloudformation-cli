# have to skip B404, subprocess is required to drive the local Docker CLI
# have to skip B603/B607, docker is invoked with a fixed, non-shell argv
"""The RQTS (CTv2 local) executor image.

:class:`RqtsImage` owns everything Docker-facing about ``cfn test --v2``: which
image to run, making it available locally, and running the container.

``cfn test --v2`` targets the executor's DirectJar handler mode::

    --extension contract-tests run-tests /work/<artifact>.zip --direct-jar \
        -r <region> -o <output-dir>

DirectJar loads the handler JAR directly into the executor JVM, so there is no
handler endpoint, no host networking, and no ``--handler-jar``/``-h``/``-tn``
flags. Inputs are packaged in the artifact zip and resolved by the executor, so
``-i`` is not emitted. Scenario selection is owned by the executor image
(capability conditions plus namespace gating of the 1P-oriented ``tagging-*``
scenarios), so no ``-s``/``--scenarios`` and no exclusion flags are emitted.

Credential secrets never enter the command line: the ``-e`` flags are name-only
and docker resolves each value from the client process environment, so the
logged command is safe and invisible to ``ps``.
"""
import logging
import os
import subprocess  # nosec B404
from pathlib import Path

from rpdk.core.exceptions import SysExitRecommendedError

from .constants import (
    CALLER_ENV_CRED_KEYS,
    CONTAINER_OUTPUT_DIR,
    CONTAINER_WORKDIR,
    ENV_CRED_KEYS,
    ENV_TYPE_CONFIGURATION,
    EXTENSION_CONTRACT_TESTS,
    HOST_OUTPUT_DIRNAME,
    PULL_ATTEMPT_TIMEOUT_SECONDS,
    PULL_MAX_ATTEMPTS,
    RQTS_IMAGE_REFERENCE,
)

LOG = logging.getLogger(__name__)


class RqtsImage:
    """The RQTS executor image: which one, whether it is here, and running it."""

    def __init__(self, reference=None):
        """Store the effective image reference.

        :param reference: image reference override, or ``None`` for the
            CLI-pinned :data:`RQTS_IMAGE_REFERENCE`.
        """
        self.reference = reference or RQTS_IMAGE_REFERENCE

    @staticmethod
    def _run_docker(args, timeout=None, env=None, capture=True):
        """Run ``docker`` with a fixed, non-shell argv.

        The single place a docker command line is assembled and invoked.

        :param list args: arguments following ``docker``
        :param timeout: optional timeout in seconds
        :param env: complete environment for the child, or ``None`` to inherit
            the ambient one. Left unset for pull and inspect so no credential
            can reach them.
        :param bool capture: capture stdout/stderr. ``False`` lets the child
            inherit the parent's terminal and stream output live as it is
            produced rather than buffering to completion (Requirement 5.1).
        :rtype: subprocess.CompletedProcess
        """
        argv = ["docker", *args]
        LOG.debug("Running: %s", " ".join(argv))
        return subprocess.run(  # nosec B603 B607
            argv,
            check=False,
            capture_output=capture,
            timeout=timeout,
            env=env,
        )

    def ensure(self):
        """Pull the image, falling back to a locally cached copy.

        A pull is attempted on every run so a moved mutable tag (``latest``) is
        picked up without a manual ``docker pull``; an up-to-date image costs
        only a manifest check. The pull is anonymous - the image is published to
        the ECR Public Gallery, so no AWS credentials are ever supplied to it.

        :raises SysExitRecommendedError: if every pull attempt fails and the
            image is not in the local image store
        """
        for attempt in range(1, PULL_MAX_ATTEMPTS + 1):
            LOG.info("Pulling RQTS image %s (attempt %d)", self.reference, attempt)
            try:
                completed = self._run_docker(
                    ["pull", self.reference], timeout=PULL_ATTEMPT_TIMEOUT_SECONDS
                )
            except (OSError, subprocess.SubprocessError) as err:
                error = err
            else:
                if completed.returncode == 0:
                    return
                error = (completed.stderr or b"").decode("utf-8", "replace").strip()
            LOG.debug(
                "Pull attempt %d for %s failed: %s", attempt, self.reference, error
            )

        try:
            cached = (
                self._run_docker(["image", "inspect", self.reference]).returncode == 0
            )
        except (OSError, subprocess.SubprocessError) as err:
            LOG.debug("Local image inspect for %s failed: %s", self.reference, err)
            cached = False

        if cached:
            LOG.warning(
                "Could not pull the RQTS image using the locally cached "
                "copy (%s), which may be stale",
                self.reference,
            )
            return

        raise SysExitRecommendedError(
            f"Failed to pull the RQTS image '{self.reference}' after "
            f"{PULL_MAX_ATTEMPTS} attempts: {error}"
        )

    def build_run_args(self, project, region, creds, type_configuration=None):
        """Build the docker ``run`` arguments and the child environment.

        Side-effect free: no subprocess, filesystem, network or AWS calls. The
        ``-e`` flags are name-only, so the returned arguments carry no secret;
        the values travel in the returned environment only.

        Composition::

            run --rm
            -e <each environment variable, by name only>
            -v <project.root>:/work
            <reference>
            --extension contract-tests run-tests /work/<artifact>.zip
            --direct-jar -r <region> -o /work/rqts-output

        :param project: the loaded :class:`rpdk.core.project.Project`. ``root``
            is the bind-mount source and ``hypenated_name`` names the artifact.
        :param str region: the effective AWS region, passed via ``-r``.
        :param creds: minted temporary credentials keyed by
            :data:`~rpdk.core.rqts.constants.ENV_CRED_KEYS`.
        :param type_configuration: the type configuration as a JSON string, or
            ``None`` to leave the variable unset so the executor falls back to
            the ``typeConfiguration`` packaged in the artifact.
        :returns: an ``(args, env)`` tuple.
        """
        # The executor reads the same credentials under both sets of names: the
        # ambient SDK chain uses AWS_*, and CALLER_AWS_* is what it repackages
        # into the handler request payload.
        env = dict(creds)
        env.update(zip(CALLER_ENV_CRED_KEYS, (creds[key] for key in ENV_CRED_KEYS)))
        if type_configuration is not None:
            env[ENV_TYPE_CONFIGURATION] = type_configuration

        args = ["run", "--rm"]
        for name in env:
            args += ["-e", name]
        # Bind mount the project root so the artifact zip is readable in-container.
        args += ["-v", f"{project.root}:{CONTAINER_WORKDIR}", self.reference]
        # The executor command: top-level --extension selector, then the
        # run-tests subcommand with the positional artifact path and DirectJar.
        args += [
            "--extension",
            EXTENSION_CONTRACT_TESTS,
            "run-tests",
            f"{CONTAINER_WORKDIR}/{project.hypenated_name}.zip",
            "--direct-jar",
            "-r",
            region,
            "-o",
            CONTAINER_OUTPUT_DIR,
        ]
        return args, env

    def run(self, project, region, creds, type_configuration=None):
        """Ensure the image, run the container, and return its exit code.

        Blocks until the container exits, streaming its output live.

        :rtype: int
        :raises SysExitRecommendedError: if the image is unavailable or the
            container process cannot be spawned
        """
        self.ensure()

        # Create the host side of the bind-mounted output directory so the
        # container's -o path exists when docker mounts it.
        (Path(project.root) / HOST_OUTPUT_DIRNAME).mkdir(parents=True, exist_ok=True)

        args, env = self.build_run_args(
            project, region, creds, type_configuration=type_configuration
        )
        try:
            return self._run_docker(
                args, env={**os.environ, **env}, capture=False
            ).returncode
        except OSError as err:
            LOG.debug("Failed to start the RQTS container", exc_info=err)
            raise SysExitRecommendedError(
                f"the RQTS container could not be started: {err}"
            ) from err
