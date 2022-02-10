from unittest.mock import Mock, patch

from rpdk.core.cli import main
from rpdk.core.project import Project


def test_generate_command_generate(capsys):
    mock_project = Mock(spec=Project)
    mock_project.type_name = "foo"

    with patch("rpdk.core.generate.Project", autospec=True, return_value=mock_project):
        main(args_in=["generate"])

    mock_project.load.assert_called_once_with()
    mock_project.generate.assert_called_once_with(None, None, [])
    mock_project.generate_docs.assert_called_once_with()

    out, err = capsys.readouterr()
    assert not err
    assert "foo" in out


def test_generate_command_generate_with_args(capsys):
    mock_project = Mock(spec=Project)
    mock_project.type_name = "foo"

    with patch("rpdk.core.generate.Project", autospec=True, return_value=mock_project):
        main(
            args_in=[
                "generate",
                "--endpoint-url",
                "http://localhost/3001",
                "--region",
                "us-east-1",
                "--target-schemas",
                "/files/target-schema.json",
                "/files/other-target-schema",
            ]
        )

    mock_project.load.assert_called_once_with()
    mock_project.generate.assert_called_once_with(
        "http://localhost/3001",
        "us-east-1",
        ["/files/target-schema.json", "/files/other-target-schema"],
    )
    mock_project.generate_docs.assert_called_once_with()

    out, err = capsys.readouterr()
    assert not err
    assert "foo" in out
