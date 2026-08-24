"""Pure argv construction for the RQTS (CTv2 local) test runner.

This module is deliberately **side-effect free**: it performs no subprocess
calls, no filesystem or network I/O, and no Docker/AWS interaction. It only
transforms already-resolved inputs (image ref, project, region) into a
``docker run`` argument list, plus the separate process-environment mapping
(:func:`build_container_env`) that carries the credential values. Keeping both
pure makes them the units that the feature's property-based tests exercise
directly. Credential secrets never enter the argv: the ``-e`` flags are
name-only and docker resolves the values from the client process environment.

``cfn test --v2`` targets the published executor image's DirectJar handler
mode. The container command produced is::

    --extension contract-tests run-tests /work/<artifact>.zip --direct-jar \
        -r <region> -o <output-dir>

DirectJar loads the handler JAR directly into the executor JVM, so there is no
handler endpoint, no host networking, and no ``--handler-jar``/``-h``/``-tn``
flags. Inputs are packaged in the artifact zip and resolved by the executor, so
``-i`` is not emitted here. Scenario selection is owned by the executor image
(capability conditions plus namespace gating of the 1P-oriented ``tagging-*``
scenarios), so no ``-s``/``--scenarios`` and no exclusion flags are emitted.
"""

from .constants import CONTAINER_OUTPUT_DIR, CONTAINER_WORKDIR, EXTENSION_CONTRACT_TESTS

# Environment variable names the RQTS executor reads for AWS access. These are
# emitted as NAME-ONLY ``-e`` flags: docker resolves each value from the docker
# client process environment (supplied via ``run_container``'s ``env``), so no
# credential value ever appears in the argv - which makes the DEBUG-logged
# command line and ``ps`` output safe by construction.
# The B105 suppressions below are false positives: these literals are
# environment-variable NAMES and credential-dict KEYS, never secret values.
_ENV_ACCESS_KEY_ID = "AWS_ACCESS_KEY_ID"
_ENV_SECRET_ACCESS_KEY = "AWS_SECRET_ACCESS_KEY"  # nosec B105
_ENV_SESSION_TOKEN = "AWS_SESSION_TOKEN"  # nosec B105
_ENV_REGION = "AWS_REGION"

# Keys used by ``boto_helpers.get_temporary_credentials`` (its default
# ``BOTO_CRED_KEYS``) to describe minted temporary credentials.
_CRED_ACCESS_KEY_ID = "aws_access_key_id"
_CRED_SECRET_ACCESS_KEY = "aws_secret_access_key"  # nosec B105
_CRED_SESSION_TOKEN = "aws_session_token"  # nosec B105


def _env_args():
    """Return the name-only ``-e`` flags for the AWS credential/region variables.

    Values are deliberately NOT embedded: docker inherits each variable from
    the docker client process environment, which the runner populates via
    :func:`build_container_env`.
    """
    return [
        "-e",
        _ENV_ACCESS_KEY_ID,
        "-e",
        _ENV_SECRET_ACCESS_KEY,
        "-e",
        _ENV_SESSION_TOKEN,
        "-e",
        _ENV_REGION,
    ]


def build_container_env(creds, region):
    """Build the environment mapping the docker client process must export.

    This is the ONLY place credential secret values are threaded: the runner
    merges this mapping into the spawned ``docker run`` process environment,
    and the argv references the variables by name only.

    :param creds: a mapping of minted temporary credentials using
        ``boto_helpers`` default keys (``aws_access_key_id``,
        ``aws_secret_access_key``, ``aws_session_token``).
    :param str region: the effective AWS region.
    :returns: dict of environment variable name -> value for the docker client.
    """
    return {
        _ENV_ACCESS_KEY_ID: creds[_CRED_ACCESS_KEY_ID],
        _ENV_SECRET_ACCESS_KEY: creds[_CRED_SECRET_ACCESS_KEY],
        _ENV_SESSION_TOKEN: creds[_CRED_SESSION_TOKEN],
        _ENV_REGION: region,
    }


def build_docker_argv(
    image_ref,
    project,
    region,
    workdir=None,
    artifact_name=None,
    output_dir=CONTAINER_OUTPUT_DIR,
):
    """Build the full ``docker run`` argv for the RQTS container (DirectJar).

    The argv contains NO credential values by construction: the ``-e`` flags
    are name-only, and the values travel through the docker client process
    environment built by :func:`build_container_env`. This keeps the argv safe
    to log at DEBUG (Req 4.10) and invisible to ``ps``.

    Composition::

        docker run --rm
        -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY
        -e AWS_SESSION_TOKEN -e AWS_REGION
        -v <workdir>:/work
        <image_ref>
        --extension contract-tests run-tests /work/<artifact_name>
        --direct-jar -r <region> -o <output_dir>

    :param str image_ref: the resolved RQTS container image reference.
    :param project: the loaded :class:`rpdk.core.project.Project`.
        ``root`` is the default bind-mount source and ``hypenated_name`` names
        the artifact zip.
    :param str region: the effective AWS region (exported as ``AWS_REGION`` via
        the process environment and passed via ``-r``).
    :param workdir: host directory to bind-mount onto :data:`CONTAINER_WORKDIR`.
        Defaults to ``str(project.root)``.
    :param artifact_name: the handler artifact zip filename inside the mount.
        Defaults to ``f"{project.hypenated_name}.zip"``.
    :param output_dir: container-internal output directory passed via ``-o``.
        Defaults to :data:`CONTAINER_OUTPUT_DIR`.
    :returns: the complete ``docker run`` argument list.
    """
    if workdir is None:
        workdir = str(project.root)
    if artifact_name is None:
        artifact_name = f"{project.hypenated_name}.zip"

    artifact_path_in_container = f"{CONTAINER_WORKDIR}/{artifact_name}"

    argv = ["docker", "run", "--rm"]
    # Credential/region variables by NAME only; values come from the process env.
    argv += _env_args()
    # Bind mount the working directory so the artifact zip is readable in-container.
    argv += ["-v", f"{workdir}:{CONTAINER_WORKDIR}"]
    # The image to run.
    argv.append(image_ref)
    # The executor command: top-level --extension selector, then the run-tests
    # subcommand with the positional artifact path and DirectJar handler mode.
    argv += [
        "--extension",
        EXTENSION_CONTRACT_TESTS,
        "run-tests",
        artifact_path_in_container,
        "--direct-jar",
        "-r",
        region,
        "-o",
        output_dir,
    ]
    # No -s/--scenarios and no --exclude-* flags: the executor image owns
    # scenario selection (capability conditions + first-party namespace gating
    # of the tagging-* scenarios), so 3P resources get the non-tagging subset
    # automatically and 1P resources run the full suite.
    return argv
