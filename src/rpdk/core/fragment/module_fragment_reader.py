import logging
import os

import yaml
from cfn_tools import load_yaml

from rpdk.core.exceptions import FragmentValidationError

LOG = logging.getLogger(__name__)
ALLOWED_EXTENSIONS = {".json", ".yaml", ".yml"}


def read_raw_fragments(fragment_dir):
    return _load_fragment(_get_fragment_file(fragment_dir))


def get_template_file_size_in_bytes(fragment_dir):
    return os.stat(_get_fragment_file(fragment_dir)).st_size


def _load_fragment(fragment_file):
    try:
        with open(fragment_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(
                __first_pass_syntax_check(__convert_function(f.read()))
            )
    except yaml.parser.ParserError as e:
        try:
            LOG.info("Parsing with cfn_flip")
            with open(fragment_file, "r", encoding="utf-8") as f:
                return load_yaml(f.read())
        except yaml.parser.ParserError as parser_error:
            raise FragmentValidationError(
                "Fragment file '{}' is invalid: {}".format(fragment_file, str(e))
            ) from parser_error


def _get_fragment_file(fragment_dir):
    all_fragment_files = []
    for root, _directories, files in os.walk(fragment_dir):
        for f in files:
            ext = os.path.splitext(f)[-1].lower()
            if ext in ALLOWED_EXTENSIONS:
                all_fragment_files.append(os.path.join(root, f))
    if len(all_fragment_files) > 1:
        raise FragmentValidationError(
            "A Module can only consist of a "
            "single template file, but there are "
            + str(len(all_fragment_files))
            + ": "
            + str(all_fragment_files)
        )
    return all_fragment_files[0]


def __first_pass_syntax_check(template):
    if "Fn::ImportValue" in template:
        raise FragmentValidationError(
            "Template fragment can't contain any Fn::ImportValue."
        )
    return template


def __convert_function(template):
    """
    When generating schema, we don't care about the actual reference.
    So the following will only make a valid YAML file.
    """
    return (
        template.replace("!Transform", "Fn::Transform")
        .replace("!ImportValue", "Fn::ImportValue")
        .replace("!", "")
    )
