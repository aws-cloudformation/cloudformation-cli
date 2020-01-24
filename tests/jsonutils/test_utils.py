import pytest

from rpdk.core.jsonutils.utils import NON_MERGABLE_KEYS, ConstraintError, schema_merge

A = "VVNEON"
B = "HVPOEV"


@pytest.mark.parametrize("key", NON_MERGABLE_KEYS)
def test_schema_merge_different_values_depth_1(key):
    with pytest.raises(ConstraintError) as excinfo:
        schema_merge({key: A}, {key: B}, ("foo",))

    message = str(excinfo.value)
    assert "#/foo" in message
    assert key in message
    assert A in message
    assert B in message


@pytest.mark.parametrize("key", NON_MERGABLE_KEYS)
def test_schema_merge_different_values_depth_2(key):
    with pytest.raises(ConstraintError) as excinfo:
        schema_merge({"Foo": {key: A}}, {"Foo": {key: B}}, ("foo",))

    message = str(excinfo.value)
    assert "#/foo/Foo" in message
    assert key in message
    assert A in message
    assert B in message


@pytest.mark.parametrize("not_a_dict", ("", 1, False, True, None, []))
def test_schema_merge_not_a_dict_lhs(not_a_dict):
    with pytest.raises(TypeError) as excinfo:
        schema_merge(not_a_dict, {}, ())

    assert "Both schemas must be dictionaries" in str(excinfo.value)


@pytest.mark.parametrize("not_a_dict", ("", 1, False, True, None, []))
def test_schema_merge_not_a_dict_rhs(not_a_dict):
    with pytest.raises(TypeError) as excinfo:
        schema_merge({}, not_a_dict, ())

    assert "Both schemas must be dictionaries" in str(excinfo.value)


def test_schema_merge_overwrite_lhs_from_rhs():
    lhs = {"foo": {"a": "aa"}, "bar": {"a": "aa"}}
    rhs = {"foo": {"a": "bb"}, "bar": {"a": "bb"}}
    result = schema_merge(lhs, rhs, ())
    assert result == {"foo": {"a": "bb"}, "bar": {"a": "bb"}}


def test_schema_merge_overwrite_and_merge():
    lhs = {"foo": {"a": {"aa": "a", "bb": "b"}}, "bar": 1}
    rhs = {"foo": {"a": {"aa": "a", "cc": "c"}}}
    result = schema_merge(lhs, rhs, ())
    assert result == {"foo": {"a": {"aa": "a", "bb": "b", "cc": "c"}}, "bar": 1}
