# pylint: disable=protected-access
import json
from unittest.mock import patch

import pytest

from rpdk.core.jsonutils.inliner import RefInliner

BASE_URI = "http://localhost/"


def make_inliner(schema, base_uri=BASE_URI):
    # this dump + load serves two purposes:
    # 1. validate JSON
    # 2. the RefInliner mutates the schema
    copy = json.loads(json.dumps(schema))
    return RefInliner(base_uri, copy)


def test_refinliner_values_are_not_walked():
    inliner = make_inliner({})
    walk_fn = inliner._walk
    # replace the walk function so it throws an error if it's called
    with patch.object(inliner, "_walk", autospec=True) as mock:
        mock.side_effect = RuntimeError
        for value in (None, True, False, 0, "", 0.0, [], {}):
            walk_fn(value, ())


def test_refinliner_objects_are_walked():
    local = {"foo": {"$ref": "#"}}
    inliner = make_inliner(local)
    inliner._walk_schema()
    assert len(inliner.ref_graph) == 1


def test_refinliner_arrays_are_walked():
    local = [{"$ref": "#"}]
    inliner = make_inliner(local)
    inliner._walk_schema()
    assert len(inliner.ref_graph) == 1


def test_refinliner_local_refs_simple_are_walked_and_unchanged():
    local = {
        "type": "object",
        "definitions": {"bar": {"type": "string"}},
        "properties": {"foo": {"$ref": "#/definitions/bar"}},
    }
    inliner = make_inliner(local)
    schema = inliner.inline()
    assert schema == local
    assert len(inliner.ref_graph) == 1


def test_refinliner_local_refs_with_base_url_are_shortened():
    ref = "#/definitions/bar"
    local = {
        "type": "object",
        "definitions": {"bar": {"type": "string"}},
        "properties": {"foo": {"$ref": BASE_URI + ref}},
    }
    inliner = make_inliner(local)
    schema = inliner.inline()
    assert schema["properties"]["foo"]["$ref"] == ref
    assert len(inliner.ref_graph) == 1


def test_refinliner_local_refs_circular_are_walked_and_unchanged():
    local = {
        "type": "object",
        "definitions": {"bar": {"$ref": "#/properties/foo"}},
        "properties": {"foo": {"$ref": "#/definitions/bar"}},
    }
    inliner = make_inliner(local)
    schema = inliner.inline()
    assert schema == local
    assert len(inliner.ref_graph) == 2


def test_refinliner_remote_refs_simple_are_walked_and_inlined(httpserver):
    target = {"type": "string"}
    remote = {"nested": {"bar": target}}
    httpserver.serve_content(json.dumps(remote))
    ref = httpserver.url + "#/nested/bar"
    inliner = make_inliner({"type": "object", "properties": {"foo": {"$ref": ref}}})
    schema = inliner.inline()
    assert schema["remote"]["schema0"]["nested"]["bar"] == target
    assert schema["properties"]["foo"]["$ref"] == "#/remote/schema0/nested/bar"
    assert len(inliner.ref_graph) == 1


def test_refinliner_remote_refs_circular_are_walked_and_inlined(httpserver):
    # these circular references result in a nonsensical schema
    # but this doesn't matter for the inliner
    ref_a = "#/properties/foo"
    remote = {"nested": {"bar": {"$ref": BASE_URI + ref_a}}}
    httpserver.serve_content(json.dumps(remote))
    ref_local = httpserver.url + "#/nested/bar"
    inliner = make_inliner(
        {"type": "object", "properties": {"foo": {"$ref": ref_local}}}
    )
    schema = inliner.inline()
    assert schema["remote"]["schema0"]["nested"]["bar"]["$ref"] == ref_a
    assert schema["properties"]["foo"]["$ref"] == "#/remote/schema0/nested/bar"
    assert len(inliner.ref_graph) == 2


def test_refinliner_remote_refs_on_filesystem_are_inlined(tmpdir):
    target = {"type": "string"}
    remote = {"nested": {"bar": target}}
    filename = tmpdir.mkdir("bar").join("remote.json")
    with filename.open("w", encoding="utf-8") as f:
        json.dump(remote, f)
    base_uri = "file://{}/foo/".format(tmpdir.strpath)
    ref = "../bar/remote.json#/nested/bar"
    inliner = make_inliner(
        {"type": "object", "properties": {"foo": {"$ref": ref}}}, base_uri=base_uri
    )
    schema = inliner.inline()
    assert schema["remote"]["schema0"]["nested"]["bar"] == target
    assert schema["properties"]["foo"]["$ref"] == "#/remote/schema0/nested/bar"
    assert len(inliner.ref_graph) == 1


def test_refinliner_rename_comment_is_added(httpserver):
    httpserver.serve_content(json.dumps({"type": "string"}))
    local = {"$ref": httpserver.url + "#"}
    inliner = make_inliner(local)
    schema = inliner.inline()
    assert schema["remote"]["schema0"]["$comment"] == httpserver.url


def test_refinliner_exiting_remote_key_is_invalid():
    with pytest.raises(ValueError):
        RefInliner("", {"remote": {}})
