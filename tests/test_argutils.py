import pytest

from rpdk.core.argutils import TextFileType


def test_textfiletype_binary_mode():
    with pytest.raises(ValueError):
        TextFileType("rb")
