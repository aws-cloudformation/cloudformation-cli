from unittest.mock import ANY, Mock, patch

from rpdk.core.build_image import _get_executable_name, build_image
from rpdk.core.cli import main
from rpdk.core.project import Project


def test_build_image():
    mock_project = Mock(spec=Project)
    mock_project.type_info = ("AWS", "color", "red")
    mock_project.runtime = "java8"
    executable_name = "aws-color-red-handler-1.0-SNAPSHOT"
    image_name = "aws-color-red"

    patch_docker = patch("rpdk.core.build_image.docker", autospec=True)
    patch_project = patch(
        "rpdk.core.build_image.Project", autospec=True, return_value=mock_project
    )

    with patch_project, patch_docker as mock_docker:
        mock_client = mock_docker.from_env.return_value
        main(args_in=["build-image"])

    mock_project.load.assert_called_once_with()
    mock_docker.from_env.assert_called_once()
    build_arguments = {
        "buildargs": {"executable_name": executable_name},
        "dockerfile": ANY,
        "path": ANY,
        "tag": image_name,
    }
    mock_client.images.build.assert_called_once_with(**build_arguments)


def test_build_image_unsupported_runtime():
    mock_project = Mock(spec=Project)
    mock_project.type_info = ("AWS", "color", "red")
    mock_project.runtime = "not_supported"

    patch_project = patch(
        "rpdk.core.build_image.Project", autospec=True, return_value=mock_project
    )

    with patch_project:
        try:
            build_image({})
        except ValueError:
            pass

    mock_project.load.assert_called_once_with()


def test_get_executable_name_unknown_runtime():
    result = _get_executable_name("not_supported", ("AWS", "color", "red"))
    assert result is None
