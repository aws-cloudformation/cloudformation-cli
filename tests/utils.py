import os
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from random import sample
from unittest.mock import Mock, patch

import pkg_resources

from rpdk.core.project import Project

CONTENTS_UTF8 = "💣"

NAMES = [
    "Apple",
    "Apricot",
    "Avocado",
    "Banana",
    "Boysenberry",
    "Blueberry",
    "Cherry",
    "Cantaloupe",
    "Clementine",
    "Cucumber",
    "Date",
    "Dewberry",
    "DragonFruit",
    "Elderberry",
    "Fig",
    "Grapefruit",
    "Grape",
    "Gooseberry",
    "Guava",
    "Kiwi",
    "Kumquat",
    "Lime",
    "Lemon",
    "Lychee",
    "Loquat",
    "Mango",
    "Mandarin",
    "Mulberry",
    "Melon",
    "Nectarine",
    "Olive",
    "Orange",
    "Papaya",
    "Persimmon",
    "Peach",
    "Pomegranate",
    "Pineapple",
    "Raspberry",
    "Strawberry",
    "Tomato",
    "Tangerine",
    "Watermelon",
]


def random_type_name():
    return "Test::{0}::{1}".format(*sample(NAMES, 2))


def random_name():
    return "-".join(sample(NAMES, 3))


@contextmanager
def chdir(path):
    old = os.getcwd()
    os.chdir(path)
    yield path
    os.chdir(old)


def add_dummy_language_plugin():
    distribution = pkg_resources.Distribution(__file__)
    entry_point = pkg_resources.EntryPoint.parse(
        "dummy = rpdk.dummy:DummyLanguagePlugin", dist=distribution
    )
    distribution._ep_map = {  # pylint: disable=protected-access
        "rpdk.v1.languages": {"dummy": entry_point}
    }
    pkg_resources.working_set.add(distribution)


def get_mock_project():
    mock_project = Mock(spec=Project)
    mock_project.load_settings.side_effect = FileNotFoundError
    mock_project.settings_path = ""
    mock_project.root = Path(".")

    patch_project = patch("rpdk.core.init.Project", return_value=mock_project)

    return (mock_project, patch_project)


def get_args(interactive=False, language=True, type_name=True):
    args = Mock(
        spec_set=[
            "force",
            "language",
            "type_name",
            "use_docker",
            "namespace",
            "codegen_model",
            "import_path",
        ]
    )
    args.force = False
    args.language = (
        None if interactive else ("dummy" if language else "invalid_language")
    )
    args.type_name = (
        None if interactive else ("Test::Test::Test" if type_name else "Test")
    )

    # The arguments below will only be tested by the plugins.
    args.use_docker = None
    args.namespace = "tested.by.the.plugin"
    args.codegen_model = None
    args.import_path = None

    return args


class UnclosingBytesIO(BytesIO):
    _was_closed = False

    def close(self):
        self._was_closed = True

    def _close(self):
        super().close()
