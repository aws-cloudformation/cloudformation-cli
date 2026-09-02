"""Constants for the RQTS (CTv2 local) contract test executor.

These values are owned by the CLI and pin the behavior of ``cfn test --v2``:
the RQTS Docker image reference, the executor extension selector, the image
pull retry policy, the bind-mount root and output directory, the environment
variables the executor reads, and the run summary messages.

``cfn test --v2`` targets the published executor image's DirectJar handler
mode, whose CLI contract is::

    --extension contract-tests run-tests <artifact> --direct-jar -r <region> -o <output>

Input subsetting (``-i``) is intentionally NOT emitted: the executor uses the
inputs packaged inside the artifact zip. Scenario subsetting (``-s``) is NOT
emitted either: scenario selection is owned by the executor image, which gates
1P-oriented scenarios (``tagging-*``) by resource-type namespace, so the CLI
passes no scenario list and no exclusions.
"""

# Fully-qualified, CLI-pinned RQTS image on the ECR Public Gallery.
# ``s5r7m5i4`` is the permanent default registry alias of the publishing
# account. The mutable ``latest`` tag is followed deliberately: the cloud
# contract-test path always runs the latest published image, and the CLI keeps
# parity by attempting a pull on every run (falling back to the local cache
# when the registry is unreachable) instead of pinning per release.
RQTS_IMAGE_REFERENCE = "public.ecr.aws/s5r7m5i4/cfn-rqts-executor-external:latest"

# The executor top-level extension selector for contract tests. Passed as the
# top-level ``--extension`` option BEFORE the ``run-tests`` subcommand.
EXTENSION_CONTRACT_TESTS = "contract-tests"

# DirectJar loads a handler JAR into the executor JVM, so only projects built by
# the Java language plugin produce a usable artifact. This is that plugin's
# ``rpdk.v1.languages`` entry point name, as recorded in ``.rpdk-config``.
JAVA_LANGUAGE = "java"

# Image pull retry policy.
PULL_MAX_ATTEMPTS = 3
PULL_ATTEMPT_TIMEOUT_SECONDS = 120

# Credential environment variables the executor's ambient SDK credential chain
# reads. Passed as ``key_names`` to ``get_temporary_credentials``, which zips
# them positionally with (AccessKeyId, SecretAccessKey, SessionToken).
ENV_CRED_KEYS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
)

# The same credential values under the names the executor repackages into the
# handler request payload. Positionally aligned with ENV_CRED_KEYS.
CALLER_ENV_CRED_KEYS = (
    "CALLER_AWS_ACCESS_KEY_ID",
    "CALLER_AWS_SECRET_ACCESS_KEY",
    "CALLER_AWS_SESSION_TOKEN",
)

# The executor reads the type configuration as JSON content from this variable,
# after the ``ct.typeConfiguration`` system property and before the
# ``typeConfiguration`` packaged in the artifact's test inputs.
ENV_TYPE_CONFIGURATION = "TYPE_CONFIGURATION"

# No AWS_REGION: the executor takes the region from ``-r``, which configures
# every SDK client it builds.

# Container-internal bind-mount root.
CONTAINER_WORKDIR = "/work"

# Directory the executor writes its output to, relative to the project root on
# the host. Created before the container runs so the bind-mounted path exists.
HOST_OUTPUT_DIRNAME = "rqts-output"

# The same directory addressed inside the container: under the bind mount, so
# results are visible on the host.
CONTAINER_OUTPUT_DIR = f"{CONTAINER_WORKDIR}/{HOST_OUTPUT_DIRNAME}"

# Overall summary lines, phrased to match the pytest path's "One or more
# contract tests failed" while naming the RQTS runner.
# B105 false positive: a log summary string, not a password.
PASS_MESSAGE = "RQTS contract tests passed"  # nosec B105
FAIL_MESSAGE = "One or more RQTS contract tests failed"

# NOTE: the CLI deliberately owns NO scenario set. The executor image decides
# which scenarios run: capability conditions (taggable/creatable/...) plus
# namespace gating that restricts the 1P-oriented ``tagging-*`` scenarios to
# reserved first-party namespaces. 3P resources therefore get the non-tagging
# subset automatically, with no scenario or exclusion flags from the CLI.
