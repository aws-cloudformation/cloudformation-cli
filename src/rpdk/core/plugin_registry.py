import pkg_resources

PLUGIN_REGISTRY = {
    entry_point.name: entry_point.load
    for entry_point in pkg_resources.iter_entry_points("rpdk.v1.languages")
}

PLUGIN_CHOICES = sorted(PLUGIN_REGISTRY.keys())


def load_plugin(language):
    return PLUGIN_REGISTRY[language]()()
