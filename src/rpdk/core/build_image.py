"""This sub command will build an image for the executable

Projects can be created via the 'init' sub command.
"""
import logging

import docker
from docker.errors import APIError, BuildError

from .exceptions import DownstreamError
from .project import Project

LOG = logging.getLogger(__name__)


def build_image(args):
    project = Project()
    project.load()

    config = project.generate_image_build_config()

    if args.executable:
        executable_name = args.executable
    else:
        executable_name = config["executable_name"]

    image_name = (
        args.image_name if args.image_name else "-".join(project.type_info).lower()
    )

    docker_client = docker.from_env()
    LOG.warning("Creating image with name '%s'", image_name)
    try:
        image, logs = docker_client.images.build(
            path=config["project_path"],
            dockerfile=config["dockerfile_path"],
            tag=image_name,
            buildargs={"executable_name": executable_name},
        )
    except (BuildError, APIError, TypeError) as e:
        raise DownstreamError("An error occurred when building the image") from e
    LOG.debug("=== Image build logs ===")
    for log in logs:
        LOG.debug(log)
    LOG.warning("Image '%s' created with id '%s'", image_name, image.id)


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
