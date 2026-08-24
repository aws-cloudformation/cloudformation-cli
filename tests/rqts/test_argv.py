"""Property-based tests for the pure argv construction module.

These tests exercise ``rpdk.core.rqts.argv`` for the executor's DirectJar
handler mode. The module under test is side-effect free, so no Docker or AWS
interaction is required: the tests only assert structural invariants of the
``docker run`` argument list it produces.

The container command produced for local DirectJar is::

    docker run --rm -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY
        -e AWS_SESSION_TOKEN -e AWS_REGION -v <workdir>:/work <image>
        --extension contract-tests run-tests /work/<artifact>.zip
        --direct-jar -r <region> -o <output-dir>

Scenario selection is owned by the executor image (capability conditions plus
first-party namespace gating), so the argv carries NO ``-s``/``--scenarios``
and NO ``--exclude-*`` flags.

The ``-e`` flags are name-only: credential values travel exclusively through
the container env mapping (``build_container_env``), never through the argv.

Library: Hypothesis (the standard Python property-based testing library). Each
property test runs at least 100 generated examples via
``@settings(max_examples=100)`` and is tagged with a comment referencing the
design property it validates.
"""
from types import SimpleNamespace

from hypothesis import given, settings, strategies as st

from rpdk.core.rqts.argv import build_container_env, build_docker_argv
from rpdk.core.rqts.constants import (
    CONTAINER_OUTPUT_DIR,
    CONTAINER_WORKDIR,
    EXTENSION_CONTRACT_TESTS,
)

# The CLI default region: ``cfn test`` defines ``--region`` with this default, so
# the effective region is always populated even when the user omits ``--region``.
CLI_DEFAULT_REGION = "us-east-1"

# Flags the DirectJar contract must NEVER emit (they belong to the old SAM Local
# / remote-lambda shapes).
FORBIDDEN_FLAGS = ("--handler-jar", "-h", "-tn", "--sam-local", "--remote-lambda")

# The tagging scenarios that ``cfn test --v2`` must NEVER run: none of these may
# appear anywhere in the argv (per product decision: no tagging tests).
FORBIDDEN_TAGGING_SCENARIOS = (
    "tagging-oob",
    "tagging-permission",
    "tagging-stack",
    "tagging-system",
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# A distinctive marker prefix used for generated credential secret values. It is
# built from characters that never appear in the type names, regions, or names
# generated below, so a secret value can be searched for reliably across the
# whole argv (Property: credentials only in env).
_SECRET_MARKER = "SECRETMARKER"

# Alphabet for type-name / region / name segments.
_SEGMENT_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

_segments = st.text(alphabet=_SEGMENT_ALPHABET, min_size=1, max_size=12)


@st.composite
def hyphenated_names(draw):
    """Generate realistic ``org-service-resource`` style hyphenated names."""
    parts = draw(st.lists(_segments, min_size=3, max_size=3))
    return "-".join(parts).lower()


# Regions: a mix of realistic region strings (including the CLI default) and
# freely generated ones.
_KNOWN_REGIONS = [
    CLI_DEFAULT_REGION,
    "us-west-2",
    "eu-west-1",
    "ap-southeast-2",
    "eu-central-1",
]
regions = st.one_of(
    st.sampled_from(_KNOWN_REGIONS),
    st.text(alphabet=_SEGMENT_ALPHABET + "-", min_size=1, max_size=20),
)


# Distinctive, searchable secret values. Each carries the marker prefix so it can
# be located anywhere in the argv without colliding with other generated data.
_secret_values = st.text(alphabet=_SEGMENT_ALPHABET, min_size=6, max_size=24).map(
    lambda body: _SECRET_MARKER + body
)


@st.composite
def credentials(draw):
    """Generate a credentials dict using the boto_helpers default keys."""
    return {
        "aws_access_key_id": draw(_secret_values),
        "aws_secret_access_key": draw(_secret_values),
        "aws_session_token": draw(_secret_values),
    }


# Working directory paths for the bind mount.
workdirs = st.text(alphabet=_SEGMENT_ALPHABET + "/", min_size=1, max_size=40).map(
    lambda p: "/" + p.strip("/")
)


def _make_project(hypenated_name, root="/project/root"):
    """Lightweight stand-in for a loaded Project (only .hypenated_name/.root used)."""
    return SimpleNamespace(hypenated_name=hypenated_name, root=root)


def _env_entries(argv):
    """Return the list of ``-e`` environment entry tokens (the token after each -e)."""
    entries = []
    for i, token in enumerate(argv):
        if token == "-e" and i + 1 < len(argv):
            entries.append(argv[i + 1])
    return entries


# ---------------------------------------------------------------------------
# Property 4
# ---------------------------------------------------------------------------
# Feature: cfn-test-v2-flag, Property 4: docker run bind-mounts the working directory onto /work
@settings(max_examples=100)
@given(
    name=hyphenated_names(),
    region=regions,
    workdir=workdirs,
)
def test_property_4_docker_run_bind_mounts_workdir(name, region, workdir):
    project = _make_project(name)
    argv = build_docker_argv("img:ref", project, region, workdir=workdir)

    # The argv must be a `docker run --rm` invocation containing a -v bind mount
    # that maps the working directory onto the container workdir.
    assert argv[:3] == ["docker", "run", "--rm"]
    expected_mount = f"{workdir}:{CONTAINER_WORKDIR}"
    assert "-v" in argv
    v_index = argv.index("-v")
    assert argv[v_index + 1] == expected_mount


# ---------------------------------------------------------------------------
# Property 5
# ---------------------------------------------------------------------------
# Feature: cfn-test-v2-flag, Property 5: credential values never enter the argv;
# they travel only through the container env mapping
@settings(max_examples=100)
@given(
    name=hyphenated_names(),
    region=regions,
    creds=credentials(),
)
def test_property_5_credentials_only_in_env_mapping_never_in_argv(name, region, creds):
    project = _make_project(name)
    argv = build_docker_argv("img:ref", project, region, workdir="/work/dir")

    env_entries = _env_entries(argv)

    # The -e flags are NAME-ONLY: the variable names are referenced so docker
    # inherits them from the client process environment; no `=` and no values.
    assert env_entries == [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_REGION",
    ]

    # No credential secret value appears ANYWHERE in the argv (this is what
    # makes the DEBUG-logged command line and `ps` output safe).
    secret_values = [
        creds["aws_access_key_id"],
        creds["aws_secret_access_key"],
        creds["aws_session_token"],
    ]
    for token in argv:
        for secret in secret_values:
            assert secret not in token
        assert "=" not in token or not token.startswith("AWS_")

    # The values travel exclusively through the container env mapping.
    env = build_container_env(creds, region)
    assert env == {
        "AWS_ACCESS_KEY_ID": creds["aws_access_key_id"],
        "AWS_SECRET_ACCESS_KEY": creds["aws_secret_access_key"],
        "AWS_SESSION_TOKEN": creds["aws_session_token"],
        "AWS_REGION": region,
    }


# ---------------------------------------------------------------------------
# Property 6
# ---------------------------------------------------------------------------
# Feature: cfn-test-v2-flag, Property 6: run-tests receives the positional artifact path inside the mount
@settings(max_examples=100)
@given(
    name=hyphenated_names(),
    region=regions,
)
def test_property_6_extension_run_tests_and_artifact_path(name, region):
    project = _make_project(name)
    argv = build_docker_argv("img:ref", project, region)

    # The top-level extension selector precedes the run-tests subcommand.
    assert "--extension" in argv
    ext_index = argv.index("--extension")
    assert argv[ext_index + 1] == EXTENSION_CONTRACT_TESTS
    assert argv[ext_index + 2] == "run-tests"

    # The positional artifact path immediately follows run-tests and is addressed
    # under the container working directory.
    artifact_path = argv[ext_index + 3]
    assert artifact_path == f"{CONTAINER_WORKDIR}/{name}.zip"
    assert artifact_path.startswith(CONTAINER_WORKDIR)


# ---------------------------------------------------------------------------
# Property 7
# ---------------------------------------------------------------------------
# Feature: cfn-test-v2-flag, Property 7: DirectJar handler mode is always selected
@settings(max_examples=100)
@given(
    name=hyphenated_names(),
    region=regions,
)
def test_property_7_direct_jar_mode_always_present(name, region):
    project = _make_project(name)
    argv = build_docker_argv("img:ref", project, region)

    assert "--direct-jar" in argv
    # And the artifact path is not itself the --direct-jar token.
    assert argv.count("--direct-jar") == 1


# ---------------------------------------------------------------------------
# Property 8
# ---------------------------------------------------------------------------
# Feature: cfn-test-v2-flag, Property 8: region argument always present with the effective region
@settings(max_examples=100)
@given(
    name=hyphenated_names(),
    # Include the default-region case explicitly by drawing a boolean that forces
    # the CLI default, mirroring "--region not supplied".
    use_default=st.booleans(),
    region=regions,
)
def test_property_8_region_argument_always_present(name, use_default, region):
    effective_region = CLI_DEFAULT_REGION if use_default else region
    project = _make_project(name)
    argv = build_docker_argv("img:ref", project, effective_region)

    assert "-r" in argv
    r_index = argv.index("-r")
    assert argv[r_index + 1] == effective_region


# ---------------------------------------------------------------------------
# Property 9
# ---------------------------------------------------------------------------
# Feature: cfn-test-v2-flag, Property 9: the old SAM Local / remote-lambda flags are never emitted
@settings(max_examples=100)
@given(
    name=hyphenated_names(),
    region=regions,
    workdir=workdirs,
)
def test_property_9_forbidden_flags_never_emitted(name, region, workdir):
    project = _make_project(name)
    argv = build_docker_argv("img:ref", project, region, workdir=workdir)

    for flag in FORBIDDEN_FLAGS:
        assert flag not in argv


# ---------------------------------------------------------------------------
# Property 10
# ---------------------------------------------------------------------------
# Feature: cfn-test-v2-flag, Property 10: no host networking is configured (DirectJar needs none)
@settings(max_examples=100)
@given(
    name=hyphenated_names(),
    region=regions,
    workdir=workdirs,
)
def test_property_10_no_host_networking(name, region, workdir):
    project = _make_project(name)
    argv = build_docker_argv("img:ref", project, region, workdir=workdir)

    argv_str = " ".join(argv)
    assert "--network" not in argv
    assert "--add-host" not in argv
    assert "host.docker.internal" not in argv_str


# ---------------------------------------------------------------------------
# Property 11
# ---------------------------------------------------------------------------
# Feature: cfn-test-v2-flag, Property 11: output directory is emitted via -o under the mount
@settings(max_examples=100)
@given(
    name=hyphenated_names(),
    region=regions,
)
def test_property_11_output_dir_emitted(name, region):
    project = _make_project(name)
    argv = build_docker_argv("img:ref", project, region)

    assert "-o" in argv
    o_index = argv.index("-o")
    assert argv[o_index + 1] == CONTAINER_OUTPUT_DIR
    # The default output dir lives under the container working directory mount.
    assert CONTAINER_OUTPUT_DIR.startswith(CONTAINER_WORKDIR)


# ---------------------------------------------------------------------------
# Property 12
# ---------------------------------------------------------------------------
# Feature: cfn-test-v2-flag, Property 12: no scenario-selection or exclusion flags
# are ever emitted; scenario selection is owned by the executor image
@settings(max_examples=100)
@given(
    name=hyphenated_names(),
    region=regions,
    workdir=workdirs,
)
def test_property_12_no_scenario_selection_or_exclusion_flags(name, region, workdir):
    project = _make_project(name)
    argv = build_docker_argv("img:ref", project, region, workdir=workdir)

    # No scenario-selection tokens: the executor decides what runs (capability
    # conditions + first-party namespace gating of the tagging-* scenarios).
    assert "-s" not in argv
    assert "--scenarios" not in argv

    # No test/check exclusion flags of any kind.
    for token in argv:
        assert not token.startswith("--exclude-")

    # No scenario name (tagging or otherwise) appears anywhere in the argv.
    for tagging_scenario in FORBIDDEN_TAGGING_SCENARIOS:
        assert tagging_scenario not in argv

    # The executor command therefore ends at the output directory.
    assert argv[-2:] == ["-o", CONTAINER_OUTPUT_DIR]


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
def test_defaults_use_project_root_and_hyphenated_name():
    """workdir defaults to str(project.root); artifact_name to <hypenated_name>.zip."""
    project = _make_project("aws-foo-bar", root="/my/project/root")
    argv = build_docker_argv("img:ref", project, "us-east-1")

    v_index = argv.index("-v")
    assert argv[v_index + 1] == f"/my/project/root:{CONTAINER_WORKDIR}"

    ext_index = argv.index("--extension")
    assert argv[ext_index + 3] == f"{CONTAINER_WORKDIR}/aws-foo-bar.zip"

    # No scenario selection: the argv ends at the output directory.
    assert "-s" not in argv
    assert argv[-2:] == ["-o", CONTAINER_OUTPUT_DIR]


# ===========================================================================
# Explicit overrides of the project-derived defaults
# ===========================================================================
def test_explicit_workdir_artifact_and_output_dir_override_defaults():
    """Supplied workdir/artifact_name/output_dir replace the project defaults.

    The defaults are derived from the project (``root`` and
    ``hypenated_name``); when a caller passes them explicitly, none of the
    project-derived values appear in the argv.
    """
    project = _make_project("aws-foo-bar", root="/project/root")

    argv = build_docker_argv(
        "img:ref",
        project,
        "us-west-2",
        workdir="/elsewhere",
        artifact_name="custom-artifact.zip",
        output_dir="/work/custom-output",
    )

    assert f"/elsewhere:{CONTAINER_WORKDIR}" in argv
    assert f"{CONTAINER_WORKDIR}/custom-artifact.zip" in argv
    assert argv[-2:] == ["-o", "/work/custom-output"]
    # None of the project-derived defaults leak in.
    assert f"/project/root:{CONTAINER_WORKDIR}" not in argv
    assert f"{CONTAINER_WORKDIR}/aws-foo-bar.zip" not in argv
    assert CONTAINER_OUTPUT_DIR not in argv
