import argparse
from unittest.mock import ANY, Mock, patch

import pytest

from rpdk.core.build_image import build_image, get_executable_name
from rpdk.core.cli import main
from rpdk.core.exceptions import DownstreamError
from rpdk.core.project import Project


@pytest.mark.parametrize(
    "command_args,expected_output",
    [
        (
            [],
            {
                "image_name": "aws-color-red",
                "executable_name": "target/aws-color-red-handler-1.0-SNAPSHOT.jar",
            },
        ),
        (
            ["--image-name", "foo"],
            {
                "image_name": "foo",
                "executable_name": "target/aws-color-red-handler-1.0-SNAPSHOT.jar",
            },
        ),
        (
            ["--executable", "target/myjar.jar"],
            {"image_name": "aws-color-red", "executable_name": "target/myjar.jar"},
        ),
    ],
)
def test_build_image(command_args, expected_output):
    mock_project = Mock(spec=Project)
    mock_project.type_info = ("AWS", "color", "red")
    mock_project.runtime = "java8"
    executable_name = expected_output["executable_name"]
    image_name = expected_output["image_name"]

    patch_docker = patch("rpdk.core.build_image.docker", autospec=True)
    patch_project = patch(
        "rpdk.core.build_image.Project", autospec=True, return_value=mock_project
    )

    with patch_project, patch_docker as mock_docker:
        mock_client = mock_docker.from_env.return_value
        main(args_in=["build-image"] + command_args)

    mock_project.load.assert_called_once_with()
    mock_docker.from_env.assert_called_once()
    build_arguments = {
        "buildargs": {"executable_name": executable_name},
        "dockerfile": ANY,
        "path": ANY,
        "tag": image_name,
    }
    mock_client.images.build.assert_called_once_with(**build_arguments)


def test_build_image_docker_error():
    mock_project = Mock(spec=Project)
    mock_project.type_info = ("AWS", "color", "red")
    mock_project.runtime = "java8"

    patch_docker = patch("rpdk.core.build_image.docker", autospec=True)
    patch_project = patch(
        "rpdk.core.build_image.Project", autospec=True, return_value=mock_project
    )

    with patch_project, patch_docker as mock_docker:
        mock_client = mock_docker.from_env.return_value
        mock_client.images.build.side_effect = TypeError("AHHH")
        try:
            args = argparse.Namespace()
            args.executable = None
            args.image_name = None
            build_image(args)
        except DownstreamError:
            pass

    mock_project.load.assert_called_once_with()
    mock_docker.from_env.assert_called_once()
    mock_client.images.build.assert_called_once()


def test_build_image_unsupported_runtime():
    mock_project = Mock(spec=Project)
    mock_project.type_info = ("AWS", "color", "red")
    mock_project.runtime = "not_supported"

    patch_project = patch(
        "rpdk.core.build_image.Project", autospec=True, return_value=mock_project
    )

    with patch_project:
        try:
            build_image(argparse.Namespace())
        except ValueError:
            pass

    mock_project.load.assert_called_once_with()


def test_get_executable_name_unknown_runtime():
    result = get_executable_name("not_supported", ("AWS", "color", "red"))
    assert result is None
