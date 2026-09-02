"""RQTS (CTv2 local) contract test runner.

:class:`RqtsRunner` orchestrates the ``cfn test --v2`` pipeline: it guards the
project artifact type, aggregates and enforces preconditions, mints temporary
AWS credentials, resolves the type configuration, then hands off to
:class:`~rpdk.core.rqts.image.RqtsImage`, which owns everything Docker-facing.

A zero container exit code logs the pass message and returns so the CLI exits
``0``; any non-zero code raises
:class:`~rpdk.core.exceptions.SysExitRecommendedError`, which ``cli.py`` maps to
``SystemExit(1)``. The per-scenario outcomes are streamed live by the container,
so the summary neither re-parses nor duplicates them.
"""

import json
import logging

from rpdk.core.exceptions import SysExitRecommendedError

from ..boto_helpers import create_sdk_session, get_temporary_credentials
from ..contract.type_configuration import TypeConfiguration
from ..project import ARTIFACT_TYPE_HOOK, ARTIFACT_TYPE_RESOURCE
from .constants import ENV_CRED_KEYS, FAIL_MESSAGE, PASS_MESSAGE
from .image import RqtsImage
from .preconditions import check_preconditions

LOG = logging.getLogger(__name__)


class RqtsRunner:
    """Orchestrates the ``cfn test --v2`` RQTS pipeline.

    A single instance owns the parsed CLI ``args`` and the loaded
    :class:`~rpdk.core.project.Project` and drives the fixed pipeline in
    :meth:`run`: artifact-type guard, precondition aggregation, credential
    minting, type configuration resolution, the container run (delegated to
    :class:`~rpdk.core.rqts.image.RqtsImage`), and exit-code mapping.

    Module projects are short-circuited upstream in ``test()`` before the runner
    is constructed, so this class only handles resource (the supported case),
    hook, and indeterminate artifact types.
    """

    def __init__(self, args, project):
        """Store the parsed CLI arguments and the loaded project.

        :param args: parsed CLI arguments (an argparse ``Namespace``). The
            runner reads ``region``, ``profile``, ``role_arn``,
            ``source_account``, ``source_arn``, ``typeconfig`` and
            ``rqts_image``.
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

        # Temporary credentials for the container, keyed by the environment
        # variables the executor reads (Requirement 3.5).
        session = create_sdk_session(self.args.region, self.args.profile)
        creds = get_temporary_credentials(
            session,
            ENV_CRED_KEYS,
            self.args.role_arn,
            headers={
                "account_id": self.args.source_account,
                "source_arn": self.args.source_arn,
            },
        )

        # TypeConfiguration memoizes the parsed file on a class attribute with no
        # invalidation, so clear it to guarantee this run reads from disk. A
        # missing file leaves the executor's variable unset, so it falls back to
        # the typeConfiguration packaged in the artifact.
        TypeConfiguration.TYPE_CONFIGURATION = None
        type_configuration = TypeConfiguration.get_type_configuration(
            self.args.typeconfig
        )

        exit_code = RqtsImage(self.args.rqts_image).run(
            self.project,
            self.args.region,
            creds,
            type_configuration=(
                json.dumps(type_configuration) if type_configuration else None
            ),
        )
        if exit_code != 0:
            raise SysExitRecommendedError(FAIL_MESSAGE)
        LOG.info(PASS_MESSAGE)
