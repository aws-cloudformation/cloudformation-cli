import pkg_resources

PLUGIN_REGISTRY = {
    entry_point.name: entry_point.load
    for entry_point in pkg_resources.iter_entry_points("rpdk.languages")
}

# mainly for unit tests
_PLUGIN_DEFAULT = "java"


def add_language_argument(parser):
    parser.add_argument(
        "--language",
        choices=list(PLUGIN_REGISTRY.keys()),
        default=_PLUGIN_DEFAULT,
        help="The language for code generation. (Default: java)",
    )


def get_plugin(language):
    return PLUGIN_REGISTRY[language]()()
