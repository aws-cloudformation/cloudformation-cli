import json
from abc import ABC, abstractmethod

import pkg_resources
from jinja2 import Environment, PackageLoader, select_autoescape

from .filters import FILTER_REGISTRY


class LanguagePlugin(ABC):
    MODULE_NAME = None

    @property
    def _module_name(self):
        if not self.MODULE_NAME:
            raise RuntimeError("Set MODULE_NAME to use parent's methods.")
        return self.MODULE_NAME

    @abstractmethod
    def project_settings_defaults(self):
        """Return a file-like object of the default project settings in YAML.

        This is so the project settings can be copied without loss of e.g. comments;
        if the project settings were parsed this would not be possible.
        """
        return pkg_resources.resource_stream(
            self._module_name, "data/project_defaults.yaml"
        )

    @abstractmethod
    def project_settings_schema(self):
        """Return the project settings schema."""
        f = pkg_resources.resource_stream(self._module_name, "data/project_schema.json")
        return json.load(f)

    def _setup_jinja_env(self, **options):
        if "loader" not in options:
            options["loader"] = PackageLoader(self._module_name, "templates/")
        if "autoescape" not in options:
            options["autoescape"] = select_autoescape(["html", "htm", "xml"])

        # bandit doesn't detect if we set "autoescape" dynamically
        env = Environment(**options)  # nosec
        for filter_name, filter_func in FILTER_REGISTRY.items():
            env.filters[filter_name] = filter_func
        return env

    @abstractmethod
    def init(self, project_settings):
        pass

    @abstractmethod
    def generate(self, resource_def, project_settings):
        pass
