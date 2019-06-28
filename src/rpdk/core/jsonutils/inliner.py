import logging
from collections.abc import Iterable, Mapping

from jsonschema import RefResolver

from .renamer import RefRenamer
from .utils import BASE, rewrite_ref, traverse

LOG = logging.getLogger(__name__)


class RefInliner(RefResolver):
    """Mutates the schema."""

    def __init__(self, base_uri, schema):
        self.schema = schema
        self.ref_graph = {}

        # our meta-schema should catch this, but better to be explicit
        if "remote" in self.schema:
            raise ValueError("Schema already contains remote schemas.")

        self.renamer = RefRenamer(renames={base_uri: BASE})
        super().__init__(base_uri=base_uri, referrer=self.schema, cache_remote=True)

    def _walk_schema(self):
        self._walk(self.schema, (BASE,))

    def _walk(self, obj, old_path):
        if isinstance(obj, str):
            return  # very common, easier to debug this case

        if isinstance(obj, Mapping):
            for key, value in obj.items():
                if key == "$ref":
                    if old_path in self.ref_graph:
                        LOG.debug("Already visited '%s' (%s)", old_path, value)
                        return
                    url, resolved = self.resolve(value)
                    LOG.debug("Resolved '%s' to '%s'", value, url)
                    # parse the URL into
                    new_path = self.renamer.parse_ref_url(url)
                    LOG.debug("Parsed '%s' to '%s'", url, new_path)
                    LOG.debug("Edge from '%s' to '%s'", old_path, new_path)
                    self.ref_graph[old_path] = new_path
                    self.push_scope(url)
                    try:
                        self._walk(resolved, new_path)
                    finally:
                        self.pop_scope()
                else:
                    self._walk(value, old_path + (key,))
        # order matters, both Mapping and strings are also Iterable
        elif isinstance(obj, Iterable):
            for i, value in enumerate(obj):
                self._walk(value, old_path + (str(i),))
        # fall-through: for other types, there's nothing to do

    def _rewrite_refs(self):
        for base_uri, rename in self.renamer.items():
            LOG.debug("Rewriting refs in '%s' (%s)", rename, base_uri)
            document = self.store[base_uri]
            for from_ref, to_ref in self.ref_graph.items():
                base, *parts = from_ref
                # only process refs in this file
                if base != rename:
                    continue
                current, _path, _parent = traverse(document, parts)
                new_ref = rewrite_ref(to_ref)
                LOG.debug("  '%s' -> '%s'", current["$ref"], new_ref)
                current["$ref"] = new_ref

    def _inline_defs(self):
        global_defs = {}
        for base_uri, rename in self.renamer.items():
            if rename is BASE:  # no need to process the local file
                continue
            LOG.debug("Inlining definitions from '%s' (%s)", rename, base_uri)
            global_defs[rename] = local_defs = {"$comment": base_uri}
            local_defs.update(self.store[base_uri])
        if global_defs:
            self.schema["remote"] = global_defs

    def inline(self):
        self._walk_schema()
        self._rewrite_refs()
        self._inline_defs()
        return self.schema
