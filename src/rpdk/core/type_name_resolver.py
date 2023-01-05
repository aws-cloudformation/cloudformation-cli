import fnmatch
import logging
import os

from botocore.exceptions import ClientError

from .exceptions import DownstreamError, InvalidTypeSchemaError

LOG = logging.getLogger(__name__)

REGISTRY_RESOURCE_TYPE = "RESOURCE"
REGISTRY_DEPRECATED_STATUS_LIVE = "LIVE"
REGISTRY_VISIBILITY_PRIVATE = "PRIVATE"
REGISTRY_VISIBILITY_PUBLIC = "PUBLIC"
REGISTRY_RESULTS_PAGE_SIZE = 100


def contains_wildcard(pattern):
    return pattern and ("*" in pattern or "?" in pattern)


class TypeNameResolver:
    def __init__(self, cfn_client):
        self.cfn_client = cfn_client

    def resolve_type_names(self, type_names):
        LOG.debug("Resolving the following type names: %s", str(type_names))

        if not any(contains_wildcard(tn) for tn in type_names):
            return type_names

        req = self._create_list_types_request(type_names)

        return self._resolve_types(type_names, self.list_applicable_types(**req).keys())

    @staticmethod
    def resolve_type_names_locally(type_names, local_info):
        LOG.debug("Resolving the following type names: %s", str(type_names))

        if not local_info:
            raise InvalidTypeSchemaError(
                "Type info must be provided for local resolving"
            )

        return TypeNameResolver._resolve_types(type_names, local_info.keys())

    @staticmethod
    def _resolve_types(type_names, applicable_types):
        types = set()
        for type_name in type_names:
            if type_name == "*":
                resolved_type_names = applicable_types
            elif contains_wildcard(type_name):
                resolved_type_names = fnmatch.filter(applicable_types, type_name)
            else:
                resolved_type_names = [type_name]

            LOG.debug(
                "'%s' resolved to the following types: %s",
                type_name,
                str(resolved_type_names),
            )
            types.update(resolved_type_names)

        return sorted(types)

    def list_applicable_types(self, **kwargs):
        kwargs["Type"] = REGISTRY_RESOURCE_TYPE
        kwargs["DeprecatedStatus"] = REGISTRY_DEPRECATED_STATUS_LIVE
        kwargs["MaxResults"] = REGISTRY_RESULTS_PAGE_SIZE

        return {
            **self._list_public_types(**kwargs),
            **self._list_private_types(**kwargs),
        }

    def _list_private_types(self, **kwargs):
        kwargs["Visibility"] = REGISTRY_VISIBILITY_PRIVATE

        return self.list_types(**kwargs)

    def _list_public_types(self, **kwargs):
        kwargs["Visibility"] = REGISTRY_VISIBILITY_PUBLIC

        return self.list_types(**kwargs)

    def list_types(self, **kwargs):
        kwargs["PaginationConfig"] = {"PageSize": REGISTRY_RESULTS_PAGE_SIZE}

        try:
            paginator = self.cfn_client.get_paginator("list_types")

            types = {}
            for page in paginator.paginate(**kwargs):
                types.update(
                    {
                        type_summary["TypeName"]: type_summary
                        for type_summary in page["TypeSummaries"]
                        if self._type_enabled(type_summary, kwargs)
                    }
                )

            return types
        except ClientError as e:
            LOG.debug("Listing types resulted in unknown ClientError", exc_info=e)
            raise DownstreamError("Unknown CloudFormation error") from e

    @staticmethod
    def _create_list_types_request(type_names):
        prefix = os.path.commonprefix(list(type_names))
        if not prefix:
            return {}

        if contains_wildcard(prefix):
            index = len(prefix)
            if "*" in prefix:
                index = min(index, prefix.index("*"))
            if "?" in prefix:
                index = min(index, prefix.index("?"))
            prefix = prefix[:index]

        req = {}
        if prefix:
            req["Filters"] = {"TypeNamePrefix": prefix}

        return req

    @staticmethod
    def _type_enabled(type_summary, request):
        if (
            request["Visibility"] == REGISTRY_VISIBILITY_PRIVATE
            or "PublisherId" not in type_summary
        ):
            return True

        return type_summary.get("IsActivated")
