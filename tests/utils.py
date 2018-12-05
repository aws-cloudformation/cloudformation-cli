import os
from contextlib import contextmanager


@contextmanager
def chdir(path):
    old = os.getcwd()
    os.chdir(path)
    yield path
    os.chdir(old)
