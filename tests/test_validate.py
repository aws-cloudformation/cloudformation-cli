from io import TextIOWrapper
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import pytest
from jsonschema.exceptions import ValidationError

from rpdk.cli import main


def test_validate_command_help(capsys):
    with patch("rpdk.validate.validate", autospec=True) as mock_validate:
        with pytest.raises(SystemExit):
            main(args_in=["validate"])
    _, err = capsys.readouterr()
    assert "usage" in err
    mock_validate.assert_not_called()


def test_validate_command_call():
    with patch("rpdk.validate.load_resource_spec", autospec=True) as mock_load:
        with NamedTemporaryFile() as f_tmp:
            main(args_in=["validate", f_tmp.name])

    mock_load.assert_called_once()
    args, kwargs = mock_load.call_args
    assert not kwargs
    assert len(args) == 1
    f_arg = args[0]
    assert isinstance(f_arg, TextIOWrapper)
    assert f_arg.name == f_tmp.name


def test_validate_command_output_valid(capsys):
    with patch("rpdk.validate.load_resource_spec", autospec=True) as mock_load:
        with NamedTemporaryFile() as f_tmp:
            main(args_in=["validate", f_tmp.name])
    out, _ = capsys.readouterr()
    assert "failed" not in out
    mock_load.assert_called_once()


def test_validate_command_output_invalid(capsys):
    with patch("rpdk.validate.load_resource_spec", autospec=True) as mock_load:
        mock_load.side_effect = ValidationError("")
        with NamedTemporaryFile() as f_tmp:
            main(args_in=["validate", f_tmp.name])
    out, _ = capsys.readouterr()
    assert "failed" in out
    mock_load.assert_called_once()
