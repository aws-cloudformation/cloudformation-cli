import os
from shutil import copyfile
from tempfile import TemporaryDirectory

from rpdk.core.fragment.lint_warning_printer import print_cfn_lint_warnings

directory = os.path.dirname(__file__)


def test_print_lint_warnings_for_unparseable_fragment_swallows_exception():
    with TemporaryDirectory() as temporary_folder:
        copyfile(
            os.path.join(directory, "../data/sample_fragments/syntax_error.json"),
            os.path.join(temporary_folder, "syntax_error.json"),
        )
        print_cfn_lint_warnings(temporary_folder)
