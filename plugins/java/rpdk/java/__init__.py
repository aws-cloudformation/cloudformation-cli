import logging
from .codegen import JavaLanguagePlugin  # noqa: F401

__version__ = "0.1"

logging.getLogger(__name__).addHandler(logging.NullHandler())
