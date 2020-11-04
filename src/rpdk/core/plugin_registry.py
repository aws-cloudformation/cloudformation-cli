import pkg_resources

PLUGIN_REGISTRY = {
    entry_point.name: entry_point.load
    for entry_point in pkg_resources.iter_entry_points("rpdk.v1.languages")
}


def get_plugin_choices():
    plugin_choices = [
        entry_point.name
        for entry_point in pkg_resources.iter_entry_points("rpdk.v1.languages")
    ]
    return sorted(set(plugin_choices))


def get_parsers():
    parsers = {
        entry_point.name: entry_point.load
        for entry_point in pkg_resources.iter_entry_points("rpdk.v1.parsers")
    }

    return parsers


def load_plugin(language):
    return PLUGIN_REGISTRY[language]()()
