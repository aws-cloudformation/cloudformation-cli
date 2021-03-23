import pytest

from rpdk.core.jsonutils.utils import (
    NON_MERGABLE_KEYS,
    ConstraintError,
    schema_merge,
    traverse_path_for_sequence_members,
)

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


def test_traverse_path_for_sequence_members_simple():
    # Arrange
    case_1 = {"foo": {"bar": [42, 43, 44]}}, ()
    result_1 = [{"foo": {"bar": [42, 43, 44]}}], [()]
    case_2 = {"foo": {"bar": [42, 43, 44]}}, ["foo"]
    result_2 = (
        [{"bar": [42, 43, 44]}],
        [tuple(["foo"])],  # noqa: C409
    )
    case_3 = {"foo": {"bar": [42, 43, 44]}}, ("foo", "bar")
    result_3 = [[42, 43, 44]], [("foo", "bar")]
    case_4_key_error = {}, ["foo"]
    case_5_value_error = [], ["foo"]
    case_6_index_error = [], [0]

    # Act
    actual_result_1 = traverse_path_for_sequence_members(*case_1)
    actual_result_2 = traverse_path_for_sequence_members(*case_2)
    actual_result_3 = traverse_path_for_sequence_members(*case_3)

    # Act/Assert
    with pytest.raises(KeyError):
        traverse_path_for_sequence_members(*case_4_key_error)
    with pytest.raises(ValueError):
        traverse_path_for_sequence_members(*case_5_value_error)
    with pytest.raises(IndexError):
        traverse_path_for_sequence_members(*case_6_index_error)

    # Assert
    assert result_1 == actual_result_1
    assert result_2 == actual_result_2
    assert result_3 == actual_result_3


def test_traverse_path_for_sequence_members_unpack():
    # Arrange
    case_1 = {"foo": {"bar": [{"baz": 1, "bin": 11}, {"baz": 2, "bin": 22}]}}, (
        "foo",
        "bar",
        "*",
    )
    result_1 = (
        [{"baz": 1, "bin": 11}, {"baz": 2, "bin": 22}],
        [("foo", "bar", 0), ("foo", "bar", 1)],
    )
    case_2 = {"foo": {"bar": [{"baz": 1, "bin": 11}, {"baz": 2, "bin": 22}]}}, (
        "foo",
        "bar",
        "*",
        "baz",
    )
    result_2 = (
        [1, 2],
        [("foo", "bar", 0, "baz"), ("foo", "bar", 1, "baz")],
    )

    # Act
    actual_result_1 = traverse_path_for_sequence_members(*case_1)
    actual_result_2 = traverse_path_for_sequence_members(*case_2)

    # Assert
    assert result_1 == actual_result_1
    assert result_2 == actual_result_2


def test_traverse_path_for_sequence_members_unpack_same_as_index():
    # Arrange
    case_1_a = {"foo": {"bar": [42, 43, 44]}}, ("foo", "bar", "0")
    case_1_b = {"foo": {"bar": [42, 43, 44]}}, ("foo", "bar", "1")
    case_1_c = {"foo": {"bar": [42, 43, 44]}}, ("foo", "bar", "2")
    result_1_a = [42], [("foo", "bar", 0)]
    result_1_b = [43], [("foo", "bar", 1)]
    result_1_c = [44], [("foo", "bar", 2)]
    case_unpack = {"foo": {"bar": [42, 43, 44]}}, ("foo", "bar", "*")
    result_unpack = (
        [42, 43, 44],
        [("foo", "bar", 0), ("foo", "bar", 1), ("foo", "bar", 2)],
    )

    # Act
    actual_result_1_a = traverse_path_for_sequence_members(*case_1_a)
    actual_result_1_b = traverse_path_for_sequence_members(*case_1_b)
    actual_result_1_c = traverse_path_for_sequence_members(*case_1_c)
    actual_result_unpack = traverse_path_for_sequence_members(*case_unpack)

    # Assert
    assert result_1_a == actual_result_1_a
    assert result_1_b == actual_result_1_b
    assert result_1_c == actual_result_1_c
    assert result_unpack == actual_result_unpack
    assert (
        actual_result_unpack[0]
        == actual_result_1_a[0] + actual_result_1_b[0] + actual_result_1_c[0]
    )
    assert (
        actual_result_unpack[1]
        == actual_result_1_a[1] + actual_result_1_b[1] + actual_result_1_c[1]
    )


def test_traverse_path_for_sequence_members_multiple_unpack():
    # Arrange
    case = {
        "bar": [
            {"baz": [{"foo": 11, "faz": 111}, {"foo": 99, "faz": 999}], "bin": 1},
            {"baz": [{"foo": 22, "faz": 222}, {"foo": 88, "faz": 888}], "bin": 2},
        ]
    }, ("bar", "*", "baz", "*", "foo")
    result = (
        [11, 99, 22, 88],
        [
            ("bar", 0, "baz", 0, "foo"),
            ("bar", 0, "baz", 1, "foo"),
            ("bar", 1, "baz", 0, "foo"),
            ("bar", 1, "baz", 1, "foo"),
        ],
    )

    # Act
    actual_result = traverse_path_for_sequence_members(*case)

    # Assert
    assert result == actual_result
