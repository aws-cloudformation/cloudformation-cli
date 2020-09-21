"""This sub command will build an image for the executable

Projects can be created via the 'init' sub command.
"""
import logging
import os

import docker
from docker.errors import APIError, BuildError

from .exceptions import DownstreamError
from .project import Project

LOG = logging.getLogger(__name__)
VALID_IMAGE_RUNTIMES = [
    "java8",
    "java11",
]


def get_executable_name(runtime, type_info):
    name = None
    if "java" in runtime:
        name = "target/" + "-".join(type_info).lower() + "-handler-1.0-SNAPSHOT.jar"
    return name


def build_image(_args):
    project = Project()
    project.load()

    if project.runtime not in VALID_IMAGE_RUNTIMES:
        raise ValueError(
            "Runtime '{}' is not supported for building an image".format(
                project.runtime
            )
        )
    if _args.executable:
        executable_name = _args.executable
    else:
        executable_name = get_executable_name(project.runtime, project.type_info)

    dockerfile_path = (
        os.path.dirname(os.path.realpath(__file__))
        + "/data/build-image-src/Dockerfile-"
        + project.runtime
    )
    project_path = os.getcwd()
    image_name = (
        _args.image_name if _args.image_name else "-".join(project.type_info).lower()
    )

    docker_client = docker.from_env()
    LOG.warning("Creating image")
    try:
        docker_client.images.build(
            path=project_path,
            dockerfile=dockerfile_path,
            tag=image_name,
            buildargs={"executable_name": executable_name},
        )
    except (BuildError, APIError, TypeError) as e:
        raise DownstreamError("An error occurred when building the image") from e
    LOG.warning("Image '%s' created", image_name)


def setup_subparser(subparsers, parents):
    # see docstring of this file
    parser = subparsers.add_parser("build-image", description=__doc__, parents=parents)
    parser.set_defaults(command=build_image)

    parser.add_argument("--image-name", help="Image name")
    parser.add_argument(
        "--executable",
        help="The relative path to the handler executable"
        " that will be built into the docker image"
        " (ie target/myjar.jar)",
    )
