import hashlib
import json
import logging
from collections.abc import Mapping, Sequence
from typing import Any, List, Tuple

from nested_lookup import nested_lookup
from ordered_set import OrderedSet

from .pointer import fragment_decode, fragment_encode

LOG = logging.getLogger(__name__)

NON_MERGABLE_KEYS = ("uniqueItems", "insertionOrder")
TYPE = "type"
REF = "$ref"
UNPACK_SEQUENCE_IDENTIFIER = "*"


class FlatteningError(Exception):
    pass


def item_hash(
    item,
):  # assumption -> input is only json comparable type (dict/list/scalar)
    """MD5 hash for an item (Dictionary/Iterable/Scalar)"""
    dhash = hashlib.md5()  # nosec
    if isinstance(item, dict):
        item = {k: item_hash(v) for k, v in item.items()}
    if isinstance(item, list):
        item = [item_hash(i) for i in item].sort()
    encoded = json.dumps(item, sort_keys=True).encode()
    dhash.update(encoded)
    return dhash.hexdigest()


def to_set(value: Any) -> OrderedSet:
    return (
        OrderedSet(value)
        if isinstance(value, (list, OrderedSet))
        else OrderedSet([value])
    )


class ConstraintError(FlatteningError, ValueError):
    def __init__(self, message, path, *args):
        self.path = fragment_encode(path)
        message = message.format(*args, path=self.path)
        super().__init__(message)


class BaseRefPlaceholder:
    """A sentinel object representing a reference inside the base document."""

    def __repr__(self):
        """Readable representation for debugging.

        >>> repr(BaseRefPlaceholder())
        '<BASE>'
        """
        return "<BASE>"


#: The sentinel instance representing a reference inside the base document.
BASE = BaseRefPlaceholder()


def rewrite_ref(ref):
    """Rewrite a reference to be inside of the base document. A relative JSON
    pointer is returned (in URI fragment identifier representation).

    If the reference is already inside the base document (:const:`BASE`), the parts
    are simply encoded into a pointer.

    If the reference is outside of the base document, a unique pointer inside
    the base document is made by namespacing the reference under the remote base
    name inside the remote section.

    >>> rewrite_ref((BASE, "foo", "bar"))
    '#/foo/bar'
    >>> rewrite_ref((BASE,))
    '#'
    >>> rewrite_ref(("remote", "foo", "bar"))
    '#/remote/remote/foo/bar'
    >>> rewrite_ref(("remote",))
    '#/remote/remote'
    """
    base, *parts = ref
    if base is not BASE:
        parts = ["remote", base] + parts
    return fragment_encode(parts)


def traverse(document, path_parts):
    """Traverse the document according to the reference.

    Since the document is presumed to be the reference's base, the base is
    discarded. There is no validation that the reference is valid.

    :raises ValueError, LookupError: the reference is invalid for this document

    >>> traverse({"foo": {"bar": [42]}}, tuple())
    ({'foo': {'bar': [42]}}, (), None)
    >>> traverse({"foo": {"bar": [42]}}, ["foo"])
    ({'bar': [42]}, ('foo',), {'foo': {'bar': [42]}})
    >>> traverse({"foo": {"bar": [42]}}, ("foo", "bar"))
    ([42], ('foo', 'bar'), {'bar': [42]})
    >>> traverse({"foo": {"bar": [42]}}, ("foo", "bar", "0"))
    (42, ('foo', 'bar', 0), [42])
    >>> traverse({}, ["foo"])
    Traceback (most recent call last):
    ...
    KeyError: 'foo'
    >>> traverse([], ["foo"])
    Traceback (most recent call last):
    ...
    ValueError: invalid literal for int() with base 10: 'foo'
    >>> traverse([], [0])
    Traceback (most recent call last):
    ...
    IndexError: list index out of range
    """
    parent = None
    path = []
    for part in path_parts:
        if isinstance(document, Sequence):
            part = int(part)
        parent = document
        document = document[part]
        path.append(part)
    return document, tuple(path), parent


def _resolve_ref(sub_schema: dict, definitions: dict, last_step: bool = False):
    # resolve $ref
    ref = nested_lookup(REF, sub_schema)  # should be safe (always single value)
    # bc sub_schema is always per paranet property
    # (taken from definitions)

    if last_step and REF not in sub_schema:  # dont traverse deeper than requested
        # check if $ref is used directly ->
        # means that we need to check definition
        # otherwise it's an array and return subschema
        return sub_schema

    if ref:
        # [0] should be a single $ref in subschema on the top level
        # [-1] $ref must follow #/definitions/object
        sub_schema = definitions[fragment_decode(ref[0])[-1]]
    # resolve properties
    properties = nested_lookup("properties", sub_schema)
    if properties:
        sub_schema = properties[0]
    return sub_schema


# pylint: disable=C0301
def traverse_raw_schema(schema: dict, path: tuple):
    """Traverse the raw json schema resolving $ref

    :raises TypeError: either schema is not of type dict
    :raises ConstraintError: the schema tries to override "type" or "$ref"

    >>> traverse_raw_schema({"properties": {"bar": [42]}}, tuple())
    {'bar': [42]}
    >>> traverse_raw_schema({"properties": {"bar": [42]}}, ("bar",))
    [42]

    >>> traverse_raw_schema({"definitions": {"bar": {"type": "boolean"}},"properties": {"bar": {"$ref": "#/definitions/bar"}}}, ("bar",))
    {'type': 'boolean'}

    >>> traverse_raw_schema({"definitions":{"b":[1],"f":{"properties":{"b":{"$ref":"#/definitions/b"}}}},"properties":{"f":{"$ref":"#/definitions/f"}}},("f", "b")) # noqa: B950
    [1]

    >>> traverse_raw_schema({}, ("foo"))
    {}
    >>> traverse_raw_schema([], ["foo"])
    Traceback (most recent call last):
    ...
    TypeError: Schema must be a dictionary
    """
    if not isinstance(schema, Mapping):
        raise TypeError("Schema must be a dictionary")

    try:
        properties = schema["properties"]
        definitions = schema.get("definitions", {})
        sub_properties = properties
        last_step = (
            len(path) - 1
        )  # get amount of steps to prevent deeper traversal than requested
        for step in path:
            sub_properties = _resolve_ref(
                sub_properties[step],
                definitions,
                last_step=path.index(step) == last_step,
            )
        return sub_properties
    except KeyError as e:
        LOG.debug("Malformed Schema or incorrect path provided\n%s\n%s", path, e)
        return {}


def traverse_path_for_sequence_members(
    document: dict, path_parts: Sequence, path: list = None
) -> Tuple[List[object], List[tuple]]:
    """Traverse the paths for all sequence members in the document according to the reference.

    Since the document is presumed to be the reference's base, the base is
    discarded. There is no validation that the reference is valid.

    Differing from traverse, this returns a list of documents and a list of resolved paths.

    :parameter document: document to traverse (dict or list)
    :parameter path_parts: document paths to traverse
    :parameter path: traversed path so far

    :raises ValueError, LookupError: the reference is invalid for this document

    >>> traverse_path_for_sequence_members({"foo": {"bar": [42, 43, 44]}}, tuple())
    ([{'foo': {'bar': [42, 43, 44]}}], [()])
    >>> traverse_path_for_sequence_members({"foo": {"bar": [42, 43, 44]}}, ["foo"])
    ([{'bar': [42, 43, 44]}], [('foo',)])
    >>> traverse_path_for_sequence_members({"foo": {"bar": [42, 43, 44]}}, ("foo", "bar"))
    ([[42, 43, 44]], [('foo', 'bar')])
    >>> traverse_path_for_sequence_members({"foo": {"bar": [42, 43, 44]}}, ("foo", "bar", "*"))
    ([42, 43, 44], [('foo', 'bar', 0), ('foo', 'bar', 1), ('foo', 'bar', 2)])
    >>> traverse_path_for_sequence_members({"foo": {"bar": [{"baz": 1, "bin": 1}, {"baz": 2, "bin": 2}]}}, ("foo", "bar", "*"))
    ([{'baz': 1, 'bin': 1}, {'baz': 2, 'bin': 2}], [('foo', 'bar', 0), ('foo', 'bar', 1)])
    >>> traverse_path_for_sequence_members({"foo": {"bar": [{"baz": 1, "bin": 1}, {"baz": 2, "bin": 2}]}}, ("foo", "bar", "*", "baz"))
    ([1, 2], [('foo', 'bar', 0, 'baz'), ('foo', 'bar', 1, 'baz')])
    >>> traverse_path_for_sequence_members({}, ["foo"])
    Traceback (most recent call last):
    ...
    KeyError: 'foo'
    >>> traverse_path_for_sequence_members([], ["foo"])
    Traceback (most recent call last):
    ...
    ValueError: invalid literal for int() with base 10: 'foo'
    >>> traverse_path_for_sequence_members([], [0])
    Traceback (most recent call last):
    ...
    IndexError: list index out of range
    """
    if path is None:
        path = []
    if not path_parts:
        return [document], [tuple(path)]
    path_parts = list(path_parts)
    if not isinstance(document, Sequence):
        return _handle_non_sequence_for_traverse(document, path_parts, path)
    return _handle_sequence_for_traverse(document, path_parts, path)


def _handle_non_sequence_for_traverse(
    current_document: dict, current_path_parts: list, current_path: list
) -> Tuple[List[object], List[tuple]]:
    """
    Handling a non-sequence member for `traverse_path_for_sequence_members` is like the loop block in `traverse`:

    The next path part is the first part in the list of path parts.
    The new document is obtained from the current document using the new path part as the key.
    The next path part is added to the traversed path.

    The traversal continues by recursively calling `traverse_path_for_sequence_members`
    """
    part_to_handle = current_path_parts.pop(0)
    current_document = current_document[part_to_handle]
    current_path.append(part_to_handle)
    return traverse_path_for_sequence_members(
        current_document, current_path_parts, current_path
    )


def _handle_sequence_for_traverse(
    current_document: Sequence, current_path_parts: list, current_path: list
) -> Tuple[List[object], List[tuple]]:
    """
    Check the new path part for the unpack sequence identifier (e.g. '*'), otherwise traverse index and continue:

    The new document is obtained from the current document (a sequence) using the new path part as the index.
    The next path part is added to the traversed path
    """
    sequence_part = current_path_parts.pop(0)
    if sequence_part == UNPACK_SEQUENCE_IDENTIFIER:
        return _handle_unpack_sequence_for_traverse(
            current_document, current_path_parts, current_path
        )
    # otherwise, sequence part should be a valid index
    current_sequence_part = int(sequence_part)
    current_document = current_document[current_sequence_part]
    current_path.append(current_sequence_part)
    return [current_document], [tuple(current_path)]


def _handle_unpack_sequence_for_traverse(
    current_document: Sequence, current_path_parts: list, current_path: list
) -> Tuple[List[object], List[tuple]]:
    """
    When unpacking a sequence, we need to include multiple paths and multiple documents, one for each sequence member.

    For each sequence member:
    Append the traversed paths w/ the sequence index, and get the new document.
    The new document is obtained by traversing the current document using the sequence index.
    The new document is appended to the list of new documents.

    For each new document:
    The remaining document is traversed using the remaining path parts.
    The list of traversed documents and traversed paths are returned.
    """
    documents = []
    resolved_paths = []
    new_documents = []
    new_paths = []
    for sequence_index in range(len(current_document)):
        new_paths.append(current_path.copy() + [sequence_index])
        new_document = traverse_path_for_sequence_members(
            current_document, [sequence_index] + current_path_parts, current_path.copy()
        )[0]
        new_documents.extend(new_document)
    for i in range(len(new_documents)):  # pylint: disable=consider-using-enumerate
        new_document = new_documents[i]
        newer_documents, newer_paths = traverse_path_for_sequence_members(
            new_document, current_path_parts, new_paths[i]
        )
        documents.extend(newer_documents)
        resolved_paths.extend(newer_paths)
    return documents, resolved_paths


def schema_merge(target, src, path):  # noqa: C901 # pylint: disable=R0912
    """Merges the src schema into the target schema in place.

    If there are duplicate keys, src will overwrite target.

    :raises TypeError: either schema is not of type dict
    :raises ConstraintError: the schema tries to override "type" or "$ref"

    >>> schema_merge({}, {}, ())
    {}
    >>> schema_merge({'foo': 'a'}, {}, ())
    {'foo': 'a'}

    >>> schema_merge({}, {'foo': 'a'}, ())
    {'foo': 'a'}

    >>> schema_merge({'foo': 'a'}, {'foo': 'b'}, ())
    {'foo': 'b'}

    >>> schema_merge({'required': 'a'}, {'required': 'b'}, ())
    {'required': ['a', 'b']}

    >>> a, b = {'$ref': 'a'}, {'foo': 'b'}
    >>> schema_merge(a, b, ('foo',))
    {'$ref': 'a', 'foo': 'b'}

    >>> a, b = {'$ref': 'a'}, {'type': 'b'}
    >>> schema_merge(a, b, ('foo',))
    {'type': OrderedSet(['a', 'b'])}

    >>> a, b = {'$ref': 'a'}, {'$ref': 'b'}
    >>> schema_merge(a, b, ('foo',))
    {'type': OrderedSet(['a', 'b'])}

    >>> a, b = {'$ref': 'a'}, {'type': ['b', 'c']}
    >>> schema_merge(a, b, ('foo',))
    {'type': OrderedSet(['a', 'b', 'c'])}

    >>> a, b = {'$ref': 'a'}, {'type': OrderedSet(['b', 'c'])}
    >>> schema_merge(a, b, ('foo',))
    {'type': OrderedSet(['a', 'b', 'c'])}

    >>> a, b = {'type': ['a', 'b']}, {'$ref': 'c'}
    >>> schema_merge(a, b, ('foo',))
    {'type': OrderedSet(['a', 'b', 'c'])}

    >>> a, b = {'type': OrderedSet(['a', 'b'])}, {'$ref': 'c'}
    >>> schema_merge(a, b, ('foo',))
    {'type': OrderedSet(['a', 'b', 'c'])}

    >>> a, b = {'Foo': {'$ref': 'a'}}, {'Foo': {'type': 'b'}}
    >>> schema_merge(a, b, ('foo',))
    {'Foo': {'type': OrderedSet(['a', 'b'])}}

    >>> schema_merge({'type': 'a'}, {'type': 'b'}, ()) # doctest: +NORMALIZE_WHITESPACE
    {'type': OrderedSet(['a', 'b'])}

    >>> schema_merge({'type': 'string'}, {'type': 'integer'}, ())
    {'type': OrderedSet(['string', 'integer'])}
    """
    if not (isinstance(target, Mapping) and isinstance(src, Mapping)):
        raise TypeError("Both schemas must be dictionaries")

    for key, src_schema in src.items():
        try:
            if key in (
                REF,
                TYPE,
            ):  # $ref and type are treated similarly and unified
                target_schema = target.get(key) or target.get(TYPE) or target[REF]
            else:
                target_schema = target[key]  # carry over existing properties
        except KeyError:
            target[key] = src_schema
        else:
            next_path = path + (key,)
            try:
                target[key] = schema_merge(target_schema, src_schema, next_path)
            except TypeError:
                if key in (TYPE, REF):  # combining multiple $ref and types
                    src_set = to_set(src_schema)

                    try:
                        target[TYPE] = to_set(
                            target[TYPE]
                        )  # casting to ordered set as lib
                        # implicitly converts strings to sets
                        target[TYPE] |= src_set
                    except (TypeError, KeyError):
                        target_set = to_set(target_schema)
                        target[TYPE] = target_set | src_set

                    try:
                        # check if there are conflicting $ref and type
                        # at the same sub schema. Conflicting $ref could only
                        # happen on combiners because method merges two json
                        # objects without losing any previous info:
                        # e.g. "oneOf": [{"$ref": "..#1.."},{"$ref": "..#2.."}] ->
                        # { "ref": "..#1..", "type": [{},{}] }
                        target.pop(REF)
                    except KeyError:
                        pass

                elif key == "required":
                    target[key] = sorted(set(target_schema) | set(src_schema))
                else:
                    if key in NON_MERGABLE_KEYS and target_schema != src_schema:
                        msg = (
                            "Object at path '{path}' declared multiple values "
                            "for '{}': found '{}' and '{}'"
                        )
                        # pylint: disable=W0707
                        raise ConstraintError(msg, path, key, target_schema, src_schema)
                    target[key] = src_schema
    return target
