"""Encode JavaScript Object Notation (JSON) Pointer as per
`RFC-6901 <https://tools.ietf.org/html/rfc6901>`_.
"""
from itertools import chain
from urllib.parse import quote, unquote


def part_encode(part):
    """Encode a part of a JSON pointer.

    >>> part_encode("foo")
    'foo'
    >>> part_encode("~foo")
    '~0foo'
    >>> part_encode("foo~")
    'foo~0'
    >>> part_encode("/foo")
    '~1foo'
    >>> part_encode("foo/")
    'foo~1'
    >>> part_encode("f/o~o")
    'f~1o~0o'
    >>> part_encode("~0")
    '~00'
    >>> part_encode("~1")
    '~01'
    >>> part_encode(0)
    '0'
    """
    return str(part).replace("~", "~0").replace("/", "~1")


def part_decode(part):
    """Decode a part of a JSON pointer.

    >>> part_decode("foo")
    'foo'
    >>> part_decode("~0foo")
    '~foo'
    >>> part_decode("foo~0")
    'foo~'
    >>> part_decode("~1foo")
    '/foo'
    >>> part_decode("foo~1")
    'foo/'
    >>> part_decode("f~1o~0o")
    'f/o~o'
    >>> part_decode("~00")
    '~0'
    >>> part_decode("~01")
    '~1'
    >>> part_decode("0")
    '0'
    """
    return part.replace("~1", "/").replace("~0", "~")


def fragment_encode(parts, prefix="#"):
    """Encode all parts of a JSON pointer into the URI fragment
    identifier representation.

    >>> fragment_encode([])
    '#'
    >>> fragment_encode([], prefix="")
    ''
    >>> fragment_encode(["foo", "bar"])
    '#/foo/bar'
    >>> fragment_encode([0, " ", "~"])
    '#/0/%20/~0'
    """
    encoded = (quote(part_encode(part), safe="/~") for part in parts)
    return "/".join(chain([prefix], encoded))


def fragment_decode(pointer, prefix="#", output=tuple):
    """Decode all segments of a JSON pointer from the URI fragment
    identifier representation.

    >>> fragment_decode("#")
    ()
    >>> fragment_decode("#/foo/bar")
    ('foo', 'bar')
    >>> fragment_decode("#/foo/bar", output=list)
    ['foo', 'bar']
    >>> fragment_decode("#/0/%20/~0")
    ('0', ' ', '~')
    >>> fragment_decode("/foo")
    Traceback (most recent call last):
    ...
    ValueError: Expected prefix '#', but was ''
    """
    segments = pointer.split("/")
    decoded = (part_decode(unquote(segment)) for segment in segments)
    actual = next(decoded)
    if prefix != actual:
        raise ValueError("Expected prefix '{}', but was '{}'".format(prefix, actual))
    return output(decoded)


def fragment_list(segments, prefix="properties", output=list):
    """Decode all segments of a JSON pointer from the URI fragment
    identifier representation.

    >>> fragment_list(["properties"])
    []
    >>> fragment_list(["properties", "foo", "bar"])
    ['foo', 'bar']
    >>> fragment_list(["properties", "foo", "bar"], output=tuple)
    ('foo', 'bar')
    >>> fragment_list(["properties", "0", "%20", "~0"])
    ['0', ' ', '~']
    >>> fragment_list(["foo"])
    Traceback (most recent call last):
    ...
    ValueError: Expected prefix 'properties', but was 'foo'
    """
    decoded = (part_decode(unquote(segment)) for segment in segments)
    actual = next(decoded)
    if prefix != actual:
        raise ValueError("Expected prefix '{}', but was '{}'".format(prefix, actual))
    return output(decoded)
