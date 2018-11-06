from collections.abc import Mapping, Sequence

from .pointer import fragment_encode


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
    name inside the definitions section.

    >>> rewrite_ref((BASE, "foo", "bar"))
    '#/foo/bar'
    >>> rewrite_ref((BASE,))
    '#'
    >>> rewrite_ref(("remote", "foo", "bar"))
    '#/definitions/remote/foo/bar'
    >>> rewrite_ref(("remote",))
    '#/definitions/remote'
    """
    base, *parts = ref
    if base is not BASE:
        parts = ["definitions", base] + parts
    return fragment_encode(parts)


def traverse(document, path_parts):
    """Traverse the document according to the reference.

    Since the document is presumed to be the reference's base, the base is
    discarded. There is no validation that the reference is valid.

    :raises ValueError, LookupError: the reference is invalid for this document

    >>> traverse({"foo": {"bar": [42]}}, tuple())
    {'foo': {'bar': [42]}}
    >>> traverse({"foo": {"bar": [42]}}, ["foo"])
    {'bar': [42]}
    >>> traverse({"foo": {"bar": [42]}}, ("foo", "bar"))
    [42]
    >>> traverse({"foo": {"bar": [42]}}, ("foo", "bar", "0"))
    42
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
    for part in path_parts:
        if isinstance(document, Sequence):
            part = int(part)
        document = document[part]
    return document


def schema_merge(target, src):
    """Merges the src schema into the target schema in place.

    If there are duplicate keys, src will overwrite target.

    :raises TypeError: either schema is not of type dict

    >>> schema_merge({}, {})
    {}
    >>> schema_merge({'foo': 'a'}, {})
    {'foo': 'a'}
    >>> schema_merge({}, {'foo': 'a'})
    {'foo': 'a'}
    >>> schema_merge({'foo': 'a'}, {'foo': 'b'})
    {'foo': 'b'}
    >>> a = {'foo': {'a': {'aa': 'a', 'bb': 'b'}}, 'bar': 1}
    >>> b = {'foo': {'a': {'aa': 'a', 'cc': 'c'}}}
    >>> schema_merge(a, b)
    {'foo': {'a': {'aa': 'a', 'bb': 'b', 'cc': 'c'}}, 'bar': 1}
    >>>
    >>> schema_merge('', {})
    Traceback (most recent call last):
    ...
    TypeError: target and src must be dictionaries
    >>>
    >>> schema_merge({}, 1)
    Traceback (most recent call last):
    ...
    TypeError: target and src must be dictionaries
    >>>
    """
    if not (isinstance(target, Mapping) and isinstance(src, Mapping)):
        raise TypeError("Both schemas must be dictionaries")
    for key, src_schema in src.items():
        try:
            target_schema = target[key]
        except KeyError:
            target[key] = src_schema
        else:
            try:
                target[key] = schema_merge(target_schema, src_schema)
            except TypeError:
                # TODO: add validation for type and $ref before overwriting keys
                target[key] = src_schema
    return target
