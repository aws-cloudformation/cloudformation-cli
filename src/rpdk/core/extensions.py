from .plugin_registry import get_extensions


def _check_command_name_collision(subparsers, command_name):
    if command_name in subparsers.choices:
        raise RuntimeError(
            f'"{command_name}" is already registered as an extension. Please use a'
            " different name."
        )


def setup_subparsers(subparsers, parents):
    extensions = get_extensions()

    for extension_cls in extensions.values():
        extension = extension_cls()()
        _check_command_name_collision(subparsers, extension.command_name)
        parser = subparsers.add_parser(extension.command_name, parents=parents)
        extension.setup_parser(parser)
