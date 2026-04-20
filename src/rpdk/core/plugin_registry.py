try:
    from importlib.metadata import entry_points as importlib_entry_points
except ImportError:  # Python < 3.8
    from importlib_metadata import entry_points as importlib_entry_points


def _iter_entry_points(group):
    eps = importlib_entry_points()
    if hasattr(eps, "select"):  # Python 3.12+
        return eps.select(group=group)
    return eps.get(group, [])


PLUGIN_REGISTRY = {
    entry_point.name: entry_point.load
    for entry_point in _iter_entry_points("rpdk.v1.languages")
}


def get_plugin_choices():
    return sorted({ep.name for ep in _iter_entry_points("rpdk.v1.languages")})


def get_parsers():
    return {ep.name: ep.load for ep in _iter_entry_points("rpdk.v1.parsers")}


def get_extensions():
    return {ep.name: ep.load for ep in _iter_entry_points("rpdk.v1.extensions")}


def load_plugin(language):
    return PLUGIN_REGISTRY[language]()()
