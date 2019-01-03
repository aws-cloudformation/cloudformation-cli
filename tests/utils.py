import os
from contextlib import contextmanager
from random import sample

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


def random_name():
    return "-".join(sample(NAMES, 3))


@contextmanager
def chdir(path):
    old = os.getcwd()
    os.chdir(path)
    yield path
    os.chdir(old)
