import json
import logging
from contextlib import contextmanager

from rpdk.core.boto_helpers import create_client
from rpdk.core.project import HANDLER_OPS, Project

from .utils import random_name, random_type_name

LOG = logging.getLogger(__name__)


@contextmanager
def handle_resource_type(project, client):
    try:
        arn = project.register()
        yield arn
    finally:
        try:
            client.delete_resource_type(Arn=arn)
        except Exception as e:  # pylint: disable=broad-except
            LOG.warning(str(e))


def test_submit_resource():
    project = Project()
    type_name = random_type_name()
    handler_arn = random_name()
    schema = {}
    project.type_name = type_name
    project.handler_arn = handler_arn
    project.schema = schema

    registry_client = create_client("cloudformation")
    with handle_resource_type(project, registry_client) as arn:
        result = registry_client.describe_resource_type(Arn=arn)

    resource_type = result["ResourceTypeDetailsList"][0]
    assert resource_type["TypeName"] == type_name
    assert all(
        resource_type["Handlers"][operation] == handler_arn for operation in HANDLER_OPS
    )
    assert resource_type["Schema"] == json.dumps(schema)
