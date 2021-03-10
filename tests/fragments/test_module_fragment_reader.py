import os
from tempfile import TemporaryDirectory

import pytest

from rpdk.core.exceptions import FragmentValidationError
from rpdk.core.fragment.module_fragment_reader import _get_fragment_file, _load_fragment

directory = os.path.dirname(__file__)


def test_fragments_are_loaded_yaml_short():
    fragment = os.path.join(directory, "../data/sample_fragments/ec2_short.yaml")
    merged_fragment = _load_fragment(fragment)
    assert len(merged_fragment) == 2
    assert len(merged_fragment["Resources"]) == 1
    assert "MyEC2Instance" in merged_fragment["Resources"]


def test_get_fragment_file_without_file_throws_exception():
    with TemporaryDirectory() as path_to_empty_directory:
        with pytest.raises(FragmentValidationError) as validation_error:
            _get_fragment_file(path_to_empty_directory)
        assert "No module fragment files found in the fragments folder" in str(
            validation_error.value
        )
