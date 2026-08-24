# have to skip B404, subprocess is required to drive the local Docker CLI
# have to skip B603/B607, docker is invoked with a fixed, non-shell argv
"""RQTS image resolution and pull-with-retry.

This module owns how ``cfn test --v2`` decides *which* RQTS container image to
run and how it makes that image available in the local Docker image store:

* :func:`resolve_image` picks the effective image reference (an explicit
  ``--rqts-image`` override, otherwise the CLI-pinned default).
* :func:`image_present_locally` reports whether the image is already in the
  local Docker image store.
* :func:`ensure_image` attempts an anonymous ``docker pull`` on every run (the
  pinned reference is a mutable ``latest`` tag, and the cloud contract-test
  path always runs the latest published image, so local runs follow it for
  parity) with a bounded per-attempt timeout and a capped number of attempts.
  When every attempt fails it falls back to the local image store with a
  warning if the image is cached, and raises
  :class:`~rpdk.core.exceptions.SysExitRecommendedError` only when no cached
  copy exists.

Docker is driven through the ``docker`` CLI via :mod:`subprocess`. The pull is
deliberately anonymous: no AWS credentials are ever supplied to it, because the
RQTS image is published to the ECR Public Gallery and is anonymously pullable.
"""
import logging
import subprocess  # nosec B404

from rpdk.core.exceptions import SysExitRecommendedError

from .constants import (
    PULL_ATTEMPT_TIMEOUT_SECONDS,
    PULL_MAX_ATTEMPTS,
    RQTS_IMAGE_REFERENCE,
)

LOG = logging.getLogger(__name__)


def resolve_image(args):
    """Resolve the effective RQTS image reference.

    Returns the ``--rqts-image`` override when it is provided and non-empty,
    otherwise the CLI-pinned :data:`RQTS_IMAGE_REFERENCE`.

    :param args: parsed CLI arguments (expects an ``rqts_image`` attribute)
    :return: the image reference to run
    :rtype: str
    """
    override = getattr(args, "rqts_image", None)
    if override:
        return override
    return RQTS_IMAGE_REFERENCE


def _run_docker(docker_args, timeout=None):
    """Run a ``docker`` subcommand with a fixed, non-shell argv.

    Kept as a small internal seam so tests can patch a single call site. No AWS
    credentials are ever injected here; the child inherits the ambient
    environment only.

    :param list docker_args: arguments following ``docker`` (for example
        ``["image", "inspect", ref]``)
    :param timeout: optional per-attempt timeout in seconds
    :return: the completed process
    :rtype: subprocess.CompletedProcess
    """
    return subprocess.run(  # nosec B603 B607
        ["docker", *docker_args],
        check=False,
        capture_output=True,
        timeout=timeout,
    )


def image_present_locally(image_ref):
    """Return whether ``image_ref`` is present in the local Docker image store.

    Uses ``docker image inspect <ref>``, which exits non-zero when the image is
    not present locally.

    :param str image_ref: the image reference to look up
    :return: ``True`` when the image is available locally, ``False`` otherwise
    :rtype: bool
    """
    try:
        completed = _run_docker(["image", "inspect", image_ref])
    except (OSError, subprocess.SubprocessError) as err:
        LOG.debug("Local image inspect for %s failed: %s", image_ref, err)
        return False
    return completed.returncode == 0


def ensure_image(image_ref):
    """Ensure ``image_ref`` is available locally, refreshing it when possible.

    A pull is attempted on **every** invocation so that a moved mutable tag
    (for example ``latest``) is picked up without manual ``docker pull``.
    The pull is anonymous (no AWS credentials) with a bounded per-attempt
    timeout of :data:`PULL_ATTEMPT_TIMEOUT_SECONDS`, retrying up to
    :data:`PULL_MAX_ATTEMPTS` times and stopping on the first success. An
    up-to-date image costs only a manifest check; no layers are re-downloaded.

    When every attempt fails, the run falls back to the local image store if
    the image is cached there (with a warning that it may be stale); only when
    no cached copy exists is the failure fatal.

    :param str image_ref: the resolved RQTS image reference
    :raises SysExitRecommendedError: if the pull fails on every attempt and
        the image is not present in the local image store
    """
    LOG.info("Pulling RQTS image %s (anonymous pull)", image_ref)
    last_error = None
    for attempt in range(1, PULL_MAX_ATTEMPTS + 1):
        LOG.debug(
            "Pulling RQTS image %s (attempt %d of %d)",
            image_ref,
            attempt,
            PULL_MAX_ATTEMPTS,
        )
        try:
            completed = _run_docker(
                ["pull", image_ref], timeout=PULL_ATTEMPT_TIMEOUT_SECONDS
            )
        except subprocess.TimeoutExpired:
            last_error = f"timed out after {PULL_ATTEMPT_TIMEOUT_SECONDS}s"
            LOG.debug("Pull attempt %d for %s %s", attempt, image_ref, last_error)
            continue
        except (OSError, subprocess.SubprocessError) as err:
            last_error = str(err)
            LOG.debug(
                "Pull attempt %d for %s failed: %s", attempt, image_ref, last_error
            )
            continue

        if completed.returncode == 0:
            LOG.debug(
                "Successfully pulled RQTS image %s on attempt %d", image_ref, attempt
            )
            return

        last_error = (completed.stderr or b"").decode("utf-8", "replace").strip() or (
            f"docker pull exited with code {completed.returncode}"
        )
        LOG.debug("Pull attempt %d for %s failed: %s", attempt, image_ref, last_error)

    if image_present_locally(image_ref):
        LOG.warning(
            "Could not pull the RQTS image '%s' (%s); using the locally cached "
            "copy, which may be stale",
            image_ref,
            last_error,
        )
        return

    raise SysExitRecommendedError(
        f"Failed to pull the RQTS image '{image_ref}' after "
        f"{PULL_MAX_ATTEMPTS} attempts: {last_error}"
    )
