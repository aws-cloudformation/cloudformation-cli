from unittest.mock import patch

import pytest

from rpdk.cli import main


def test_init_command_help(capsys):
    with patch("rpdk.init.init", autospec=True) as mock_init:
        with pytest.raises(SystemExit):
            main(args_in=["init", "--help"])  # init has no required params
    out, _ = capsys.readouterr()
    assert "--help" in out
    mock_init.assert_not_called()
