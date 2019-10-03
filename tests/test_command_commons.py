from unittest.mock import Mock, patch

import pytest

from rpdk.core.cli import EXIT_UNHANDLED_EXCEPTION, main
from rpdk.core.project import Project


@pytest.mark.parametrize(
    "command", ["init", "generate", "submit", "validate", "test", "invoke"]
)
def test_command_help(capsys, command):
    with patch("rpdk.core.{0}.{0}".format(command), autospec=True) as mock_func:
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=[command, "--help"])
    assert excinfo.value.code != EXIT_UNHANDLED_EXCEPTION
    out, _ = capsys.readouterr()
    assert "--help" in out
    mock_func.assert_not_called()


@pytest.mark.parametrize("command", ["invoke"])
def test_command_with_required_params(capsys, command):
    with patch("rpdk.core.{0}.{0}".format(command), autospec=True) as mock_func:
        with pytest.raises(SystemExit) as excinfo:
            main(args_in=[command])
    assert excinfo.value.code != EXIT_UNHANDLED_EXCEPTION
    _, err = capsys.readouterr()
    assert "the following arguments are required" in err
    mock_func.assert_not_called()


@pytest.mark.parametrize("command", ["submit", "validate", "generate"])
def test_command_default(command):
    mock_project = Mock(spec=Project)
    with patch(
        "rpdk.core.{0}.Project".format(command),
        autospec=True,
        return_value=mock_project,
    ):
        main(args_in=[command])

    mock_project.load.assert_called_once_with()
    try:
        getattr(mock_project, command).assert_called_once()
    except AttributeError:
        pass
