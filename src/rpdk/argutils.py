from argparse import FileType


class TextFileType(FileType):
    def __init__(self, mode):
        if "b" in mode:
            raise ValueError("binary mode")
        super().__init__(mode, encoding="utf-8")
