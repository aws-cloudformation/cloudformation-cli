from collections.abc import Mapping, Sequence

from .pointer import fragment_encode

NON_MERGABLE_KEYS = ("$ref", "uniqueItems", "insertionOrder")


class FlatteningError(Exception):
    pass


class ConstraintError(FlatteningError, ValueError):
    def __init__(self, message, path, *args):
        self.path = fragment_encode(path)
        message = message.format(*args, path=self.path)
        super().__init__(message)


class CircularRefError(ConstraintError):
    def __init__(self, path):
        super().__init__("Detected circular reference at '{path}'", path)


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


# pylint: disable=R0913,C0301
# flake8: noqa=C901,B950
def traverse_list_safe(
    document,
    path_parts,
    parent=None,
    path=None,
    paths=None,
    documents=None,
    parents=None,
):
    """Traverse the document according to the reference.
    This method traverses all the elements of the lists
    and returns their corresponding document, path, parent

    Since the document is presumed to be the reference's base, the base is
    discarded. There is no validation that the reference is valid.

    :raises ValueError, LookupError: the reference is invalid for this document

    >>> traverse_list_safe({"foo": {"bar": [42]}}, tuple())
    ([{'foo': {'bar': [42]}}], [None], [None])
    >>> traverse_list_safe({"foo": {"bar": [42]}}, ["foo"])
    ([{'bar': [42]}], [['foo']], [{'foo': {'bar': [42]}}])
    >>> traverse_list_safe({"foo": {"bar": [42]}}, ("foo", "bar"))
    ([[42]], [['foo', 'bar']], [{'bar': [42]}])
    >>> traverse_list_safe({"foo": {"bar": [42]}}, ("foo", "bar", "0"))
    ([42], [['foo', 'bar', 0]], [[42]])
    >>> traverse_list_safe({"foo": {"bar": [42, 21, 32]}}, ("foo", "bar", "*"))
    ([42, 21, 32], [['foo', 'bar', 0], ['foo', 'bar', 1], ['foo', 'bar', 2]], [[42, 21, 32], [42, 21, 32], [42, 21, 32]])
    >>> traverse_list_safe({}, ["foo"])
    Traceback (most recent call last):
    ...
    KeyError: 'foo'
    >>> traverse_list_safe([], ["foo"])
    Traceback (most recent call last):
    ...
    ValueError: invalid literal for int() with base 10: 'foo'
    >>> traverse_list_safe([], [0])
    Traceback (most recent call last):
    ...
    IndexError: list index out of range
    """
    if not path_parts:
        if not paths:
            paths = []
        paths.append(path)

        if not documents:
            documents = []
        documents.append(document)

        if not parents:
            parents = []
        parents.append(parent)

        return documents, paths, parents

    temp_path = path_parts[0]
    if isinstance(document, Sequence):
        if temp_path == "*":
            index = 0
            path_copy = path.copy()
            while True:
                temp_path = index
                path = path_copy.copy()
                try:
                    path.append(temp_path)
                    documents, paths, parents = traverse_list_safe(
                        document[temp_path],
                        path_parts[1:],
                        document,
                        path,
                        paths,
                        documents,
                        parents,
                    )
                    index += 1
                except LookupError:
                    break
            return documents, paths, parents
        temp_path = int(temp_path)

    if not path:
        path = []
    path.append(temp_path)
    return traverse_list_safe(
        document[temp_path], path_parts[1:], document, path, paths, documents, parents
    )


def schema_merge(target, src, path):  # noqa: C901
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
    >>> a, b = {'$ref': 'a'}, {'type': 'b'}
    >>> schema_merge(a, b, ('foo',))
    {'$ref': 'a', 'type': 'b'}
    >>> a, b = {'Foo': {'$ref': 'a'}}, {'Foo': {'type': 'b'}}
    >>> schema_merge(a, b, ('foo',))
    {'Foo': {'$ref': 'a', 'type': 'b'}}
    >>> schema_merge({'type': 'a'}, {'type': 'b'}, ()) # doctest: +NORMALIZE_WHITESPACE
    {'type': ['a', 'b']}
    """
    if not (isinstance(target, Mapping) and isinstance(src, Mapping)):
        raise TypeError("Both schemas must be dictionaries")

    for key, src_schema in src.items():
        try:
            target_schema = target[key]
        except KeyError:
            target[key] = src_schema
        else:
            next_path = path + (key,)
            try:
                target[key] = schema_merge(target_schema, src_schema, next_path)
            except TypeError:
                if key == "type":
                    if isinstance(target_schema, list):
                        target_schema.append(src_schema)
                        continue
                    target[key] = [target_schema, src_schema]
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
