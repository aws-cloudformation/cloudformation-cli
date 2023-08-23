from .plugin_registry import get_extensions


def setup_subparsers(subparsers, parents):
    extensions = get_extensions()

    for extension_cls in extensions.values():
        extension = extension_cls()()
        parser = subparsers.add_parser(extension.command_name, parents=parents)
        extension.setup_parser(parser)
