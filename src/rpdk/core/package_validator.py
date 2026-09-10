"""Validation utilities for pre-built schema handler packages.

This module supports the ``cfn submit --package <path>`` workflow, in which a
user submits a zip file that was already built (for example, by a previous
``cfn submit --dry-run`` or by a CI pipeline). The validator opens the zip,
extracts the minimum metadata required to call ``RegisterType``, and reports
any problems via :class:`rpdk.core.exceptions.InvalidProjectError`.

The validator does not mutate the zip or the working directory, and does not
require a ``.rpdk-config`` in the current working directory.
"""
import json
import logging
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from .exceptions import InvalidProjectError

LOG = logging.getLogger(__name__)

SETTINGS_FILENAME = ".rpdk-config"
SCHEMA_FILENAME = "schema.json"
METADATA_FILENAME = ".cfn_metadata.json"

ARTIFACT_TYPE_RESOURCE = "RESOURCE"
ARTIFACT_TYPE_MODULE = "MODULE"
ARTIFACT_TYPE_HOOK = "HOOK"
SUPPORTED_ARTIFACT_TYPES = frozenset(
    {ARTIFACT_TYPE_RESOURCE, ARTIFACT_TYPE_MODULE, ARTIFACT_TYPE_HOOK}
)


@dataclass(frozen=True)
class PackageMetadata:
    """Minimal information about a pre-built package, extracted from its zip.

    Attributes:
        path: Filesystem path to the original zip file. The caller is
            expected to re-open this path as a binary file object when it is
            ready to upload the bytes.
        type_name: The ``typeName`` declared in the zip's ``.rpdk-config``
            entry (for example ``"Acme::Example::Widget"``).
        artifact_type: One of ``"RESOURCE"``, ``"MODULE"`` or ``"HOOK"``.
    """

    path: Path
    type_name: str
    artifact_type: str


class PackageValidator:
    """Validate a pre-built schema handler package zip and extract metadata.

    The validator never writes to the filesystem and never consults the
    current working directory. All validation is performed against the zip
    file whose path is given to the constructor.

    Usage::

        metadata = PackageValidator(Path("./my-type.zip")).validate()
        # metadata.type_name and metadata.artifact_type are ready to be
        # passed to the CloudFormation RegisterType API.

    On any validation failure, :class:`rpdk.core.exceptions.InvalidProjectError`
    is raised. The exception message is expected to name the offending input
    (file path, missing entry, invalid field) so that the CLI can surface a
    clear error to the user.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def validate(self) -> PackageMetadata:
        """Run the full validation pipeline and return a :class:`PackageMetadata`.

        The pipeline steps, in order:

        1. Open the zip archive (existence + format check).
        2. Read and parse the ``.rpdk-config`` entry inside the zip.
        3. Resolve the ``artifact_type`` field (with a RESOURCE fallback).
        4. Assert that all required entries for the resolved artifact type
           are present (currently: ``schema.json``).
        5. Opportunistically log metadata from ``.cfn_metadata.json`` if it
           is present.
        6. Return a :class:`PackageMetadata` built from the zip contents.
        """
        with self._open_zip() as zip_file:
            settings = self._read_settings(zip_file)
            artifact_type = self._resolve_artifact_type(settings)
            type_name = self._require_type_name(settings)
            self._assert_required_entries(zip_file, artifact_type)
            self._log_metadata_if_present(zip_file)

        return PackageMetadata(
            path=self.path,
            type_name=type_name,
            artifact_type=artifact_type,
        )

    # ------------------------------------------------------------------
    # Internal helpers. Each step of the validation pipeline is split
    # into a small private method so that error messages stay close to
    # the check that produced them and the control flow in ``validate``
    # remains easy to read.
    # ------------------------------------------------------------------

    def _open_zip(self) -> zipfile.ZipFile:
        """Open ``self.path`` as a zip archive.

        Raises:
            InvalidProjectError: If the path does not exist, is not a file,
                or is not a readable zip archive. The error message always
                names the offending path.
        """
        if not self.path.is_file():
            raise InvalidProjectError(f"Package file '{self.path}' does not exist.")
        try:
            return zipfile.ZipFile(self.path, mode="r")
        except zipfile.BadZipFile as exc:
            raise InvalidProjectError(
                f"Package file '{self.path}' is not a valid zip archive."
            ) from exc

    def _read_settings(self, zip_file: zipfile.ZipFile) -> Dict[str, Any]:
        """Read and parse the ``.rpdk-config`` entry inside the zip.

        Raises:
            InvalidProjectError: If the zip does not contain ``.rpdk-config``
                or the entry cannot be parsed as JSON.
        """
        if SETTINGS_FILENAME not in zip_file.namelist():
            raise InvalidProjectError(
                f"Package file '{self.path}' is missing required entry "
                f"'{SETTINGS_FILENAME}'."
            )
        try:
            with zip_file.open(SETTINGS_FILENAME, mode="r") as entry:
                raw = entry.read()
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InvalidProjectError(
                f"Settings file '{SETTINGS_FILENAME}' in package "
                f"'{self.path}' is not valid JSON."
            ) from exc

    def _resolve_artifact_type(self, settings: Dict[str, Any]) -> str:
        """Return the artifact type declared in ``settings``.

        Falls back to :data:`ARTIFACT_TYPE_RESOURCE` for backward
        compatibility when the field is absent (legacy packages written
        before the CLI started emitting ``artifact_type``).

        Raises:
            InvalidProjectError: If ``artifact_type`` is present but is not
                one of :data:`SUPPORTED_ARTIFACT_TYPES`.
        """
        if "artifact_type" not in settings:
            return ARTIFACT_TYPE_RESOURCE

        artifact_type = settings["artifact_type"]
        if artifact_type not in SUPPORTED_ARTIFACT_TYPES:
            raise InvalidProjectError(
                f"Settings file '{SETTINGS_FILENAME}' in package "
                f"'{self.path}' declares an unsupported artifact_type "
                f"{artifact_type!r}. Expected one of "
                f"{sorted(SUPPORTED_ARTIFACT_TYPES)}."
            )
        return artifact_type

    def _require_type_name(self, settings: Dict[str, Any]) -> str:
        """Return the ``typeName`` field from ``settings``.

        Raises:
            InvalidProjectError: If ``typeName`` is missing or empty.
        """
        type_name = settings.get("typeName")
        if not type_name:
            raise InvalidProjectError(
                f"Settings file '{SETTINGS_FILENAME}' in package "
                f"'{self.path}' is missing required field 'typeName'."
            )
        return type_name

    def _assert_required_entries(
        self, zip_file: zipfile.ZipFile, artifact_type: str
    ) -> None:
        """Verify that every entry required for ``artifact_type`` is present.

        Currently every supported artifact type (RESOURCE / MODULE / HOOK)
        is required to ship a ``schema.json`` entry. The ``artifact_type``
        parameter is kept in the signature so that the validator can
        diverge per-type without changing its caller.

        Raises:
            InvalidProjectError: If a required entry is missing.
        """
        del artifact_type  # currently unused; future-proofed in signature
        if SCHEMA_FILENAME not in zip_file.namelist():
            raise InvalidProjectError(
                f"Package file '{self.path}' is missing required entry "
                f"'{SCHEMA_FILENAME}'."
            )

    def _log_metadata_if_present(self, zip_file: zipfile.ZipFile) -> None:
        """Log metadata about the package if ``.cfn_metadata.json`` is present.

        The metadata file is informational only. Parse failures or missing
        fields must not abort validation, so problems are logged at WARNING
        and execution continues.
        """
        if METADATA_FILENAME not in zip_file.namelist():
            return

        try:
            with zip_file.open(METADATA_FILENAME, mode="r") as entry:
                raw = entry.read()
            metadata = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            LOG.warning(
                "Package '%s' has a '%s' entry that could not be parsed as JSON: %s",
                self.path,
                METADATA_FILENAME,
                exc,
            )
            return

        if not isinstance(metadata, dict):
            LOG.warning(
                "Package '%s' has a '%s' entry that is not a JSON object; ignoring.",
                self.path,
                METADATA_FILENAME,
            )
            return

        cli_version = metadata.get("cli-version")
        if cli_version is None:
            LOG.warning(
                "Package '%s' has a '%s' entry without a 'cli-version' field.",
                self.path,
                METADATA_FILENAME,
            )
            return

        LOG.info(
            "Package '%s' was built with cfn-cli version %s.",
            self.path,
            cli_version,
        )
