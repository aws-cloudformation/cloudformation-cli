import logging

LOG = logging.getLogger(__name__)


def generate_handler_name(operation):
    if operation.endswith("_PROVISION"):
        # CREATE_PRE_PROVISION -> preCreate
        *action, prefix = operation.split("_PROVISION")[0].split("_")
    else:
        # CREATE -> create
        # SOME_OPERATION -> someOperation
        prefix, *action = operation.split("_")

    handler_name = prefix.lower() + "".join(act.title() for act in action)

    return handler_name
