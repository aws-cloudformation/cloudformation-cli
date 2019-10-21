import pytest


def contract_check_asserts_work():
    message = (
        "Asserts have been stripped. This is unusual, but happens if the "
        "contract tests are compiled to optimized byte code. As a result, the "
        "contract tests will not run correctly. Please raise an issue with "
        "as much information about your system and runtime as possible."
    )
    with pytest.raises(AssertionError):
        assert False  # noqa: B011
        pytest.fail(message)
