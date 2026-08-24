"""Constants for the RQTS (CTv2 local) contract test executor.

These values are owned by the CLI and pin the behavior of ``cfn test --v2``:
the RQTS Docker image reference, the executor extension selector, the image
pull retry policy, and the container-internal bind-mount root and output
directory.

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

# SAM Local handler port. Retained for reference; unused by the DirectJar mode
# that ``cfn test --v2`` targets (DirectJar loads the handler in-process and
# needs no handler endpoint).
DEFAULT_HANDLER_PORT = 3031

# Image pull retry policy (Req 2.4).
PULL_MAX_ATTEMPTS = 3
PULL_ATTEMPT_TIMEOUT_SECONDS = 120

# Container-internal bind-mount root.
CONTAINER_WORKDIR = "/work"

# Container-internal directory the executor writes its output to (under the
# bind mount, so results are visible on the host).
CONTAINER_OUTPUT_DIR = "/work/rqts-output"

# NOTE: the CLI deliberately owns NO scenario set. The executor image decides
# which scenarios run: capability conditions (taggable/creatable/...) plus
# namespace gating that restricts the 1P-oriented ``tagging-*`` scenarios to
# reserved first-party namespaces. 3P resources therefore get the non-tagging
# subset automatically, with no scenario or exclusion flags from the CLI.
