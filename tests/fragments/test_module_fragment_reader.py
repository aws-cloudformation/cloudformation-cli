import os

from rpdk.core.fragment.module_fragment_reader import _load_fragment

directory = os.path.dirname(__file__)


def test_fragments_are_loaded_yaml_short():
    fragment = os.path.join(directory, "../data/sample_fragments/ec2_short.yaml")
    merged_fragment = _load_fragment(fragment)
    assert len(merged_fragment) == 2
    assert len(merged_fragment["Resources"]) == 1
    assert "MyEC2Instance" in merged_fragment["Resources"]
