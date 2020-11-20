from collections.abc import Mapping, Sequence
from typing import Any

from ordered_set import OrderedSet

from .pointer import fragment_encode

NON_MERGABLE_KEYS = ("uniqueItems", "insertionOrder")
TYPE = "type"
REF = "$ref"


class FlatteningError(Exception):
    pass


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
