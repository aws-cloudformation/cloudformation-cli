import pkg_resources

PLUGIN_REGISTRY = {
    entry_point.name: entry_point.load()()
    for entry_point in pkg_resources.iter_entry_points("rpdk.languages")
}


def add_language_argument(parser):
    parser.add_argument(
        "--language",
        choices=list(PLUGIN_REGISTRY.keys()),
        default="java",
        help="The language for code generation. (Default: java)",
    )
