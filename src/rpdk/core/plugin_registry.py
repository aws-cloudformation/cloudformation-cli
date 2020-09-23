import pkg_resources

PLUGIN_REGISTRY = {
    entry_point.name: entry_point.load
    for entry_point in pkg_resources.iter_entry_points("rpdk.v1.languages")
}

PARSER_REGISTRY = {
    entry_point.name: entry_point.load
    for entry_point in pkg_resources.iter_entry_points("rpdk.v1.parsers")
}


def get_plugin_choices():
    plugin_choices = [
        entry_point.name
        for entry_point in pkg_resources.iter_entry_points("rpdk.v1.languages")
    ]
    return sorted(plugin_choices)

def get_parsers():
    return PARSER_REGISTRY

def load_plugin(language):
    return PLUGIN_REGISTRY[language]()()
