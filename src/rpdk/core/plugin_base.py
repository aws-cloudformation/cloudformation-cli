import importlib
import os
from abc import ABC, abstractmethod

from jinja2 import (
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PackageLoader,
    select_autoescape,
)

from .filters import FILTER_REGISTRY


class LanguagePlugin(ABC):
    MODULE_NAME = None

    @property
    def _module_name(self):
        if not self.MODULE_NAME:
            raise RuntimeError("Set MODULE_NAME to use parent's methods.")
        return self.MODULE_NAME

    def _setup_jinja_env(self, **options):

        if "loader" not in options:
            # Try loading module with PEP 451 loaders
            spec = importlib.util.find_spec(self._module_name)

            loader = (
                FileSystemLoader(
                    os.path.join(os.path.dirname(spec.origin), "templates")
                )
                if spec is not None
                else PackageLoader(self._module_name)
            )

            options["loader"] = ChoiceLoader([loader, PackageLoader(__name__)])
        if "autoescape" not in options:
            options["autoescape"] = select_autoescape(["html", "htm", "xml"])

        # bandit doesn't detect if we set "autoescape" dynamically
        env = Environment(**options)  # nosec
        for filter_name, filter_func in FILTER_REGISTRY.items():
            env.filters[filter_name] = filter_func
        return env

    @abstractmethod
    def init(self, project):
        pass

    @abstractmethod
    def generate(self, project):
        pass

    @abstractmethod
    def package(self, project, zip_file):
        pass
