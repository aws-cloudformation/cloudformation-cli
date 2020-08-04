from functools import wraps
from inspect import Parameter, signature

import pytest


def _rebind(decorator, func, *args, **kwargs):
    """Helper function to construct decorated arguments

    This works only with positional and likely positional arguments
    strongly keyword arguments are in **kwargs. It constructs kwargs'
    from positional values
    """
    parameters = signature(func).parameters.values()
    decorated_parameters = set(signature(decorator).parameters.keys())

    positional_kwargs = dict(
        zip(
            [
                parameter.name
                for parameter in parameters
                if parameter.kind
                in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
                and parameter.name not in kwargs
            ],
            args,
        )
    )
    return {k: kwargs.get(k) or positional_kwargs[k] for k in decorated_parameters}


def decorate(after=True):
    """Helper function to construct decorator from a simple function

    arg: after means that decorated check should be run after the
    target function

    This is a 'decorate' meta function that wraps new decorator around
    target function and merges decorated arguments with target arguments
    convention: each new decorator should have a 'response' argument,
    which is an output of a target function
    """

    def inner_decorator(decorator: object):
        def new_decorator(func: object):
            @wraps(func)
            def function(*args, **kwargs):
                response_arg = {}
                if after:  # running function before the decorated check
                    response = func(*args, **kwargs)  # calling target function
                    response_arg = {"response": response}

                kvargs = _rebind(decorator, func, *args, **{**kwargs, **response_arg})
                decorated_sig = signature(decorator)
                bound_arguments = decorated_sig.bind(**kvargs)
                decorator(
                    *bound_arguments.args, **bound_arguments.kwargs
                )  # calling a decorated function to execute check

                # this allows to make a pre-execution check
                # e.g. if skip function
                if not after:  # running function after the decorated check
                    response = func(*args, **kwargs)  # calling target function
                return response

            return function

        return new_decorator

    return inner_decorator


@decorate()
def response_does_not_contain_write_only_properties(resource_client, response):
    resource_client.assert_write_only_property_does_not_exist(response["resourceModel"])


@decorate()
def response_contains_resource_model_equal_current_model(
    response, current_resource_model
):
    assert response["resourceModel"] == current_resource_model


@decorate()
def response_contains_resource_model_equal_updated_model(
    response, current_resource_model, update_resource_model
):
    assert response["resourceModel"] == {
        **current_resource_model,
        **update_resource_model,
    }


@decorate()
def response_contains_primary_identifier(resource_client, response):
    resource_client.assert_primary_identifier(
        resource_client.primary_identifier_paths, response["resourceModel"]
    )


@decorate()
def response_contains_unchanged_primary_identifier(
    resource_client, response, current_resource_model
):
    resource_client.is_primary_identifier_equal(
        resource_client.primary_identifier_paths,
        current_resource_model,
        response["resourceModel"],
    )


@decorate(after=False)
def skip_not_writable_identifier(resource_client):
    if not resource_client.has_writable_identifier():
        pytest.skip("No writable identifiers. Skipping test.")


def failed_event(error_code, msg=""):
    def decorator_wrapper(func: object):
        @wraps(func)
        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            if response is not None:
                assert response == error_code, msg
            return response

        return wrapper

    return decorator_wrapper
