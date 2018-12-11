from ..utils import safe_reserved


def test_safe_reserved_safe_string():
    assert safe_reserved("foo") == "foo"


def test_safe_reserved_unsafe_string():
    assert safe_reserved("class") == "class_"
