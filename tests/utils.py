import os
from contextlib import contextmanager
from io import BytesIO
from random import sample

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


class UnclosingBytesIO(BytesIO):
    _was_closed = False

    def close(self):
        self._was_closed = True

    def _close(self):
        super().close()
