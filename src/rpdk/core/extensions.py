from .plugin_registry import get_extensions


def setup_subparsers(subparsers, parents):
    extensions = get_extensions()

    for extension_cls in extensions.values():
        extension = extension_cls()()
        extension.setup_subparser(subparsers, parents)
