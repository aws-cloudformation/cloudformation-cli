"""
This class has two responsibilities:
1. generating a sample template fragment so the user has some initial
file fragment as an example.
The method "generate_sample_fragment" will be called as part of the init command.
2. generating schema for provided template fragments.
The method "generate_schema" will be called right before submission.
"""
import json
import logging
import os
from pathlib import Path

from rpdk.core.data_loaders import resource_json
from rpdk.core.exceptions import FragmentValidationError

from .lint_warning_printer import print_cfn_lint_warnings
from .module_fragment_reader import get_template_file_size_in_bytes, read_raw_fragments

LOG = logging.getLogger(__name__)
FRAGMENT_DIR = "fragments"
SAMPLE_FRAGMENT_OUTPUT = "sample.json"
SCHEMA_NAME = "schema.json"
SAMPLE_FRAGMENT = "../data/examples/module/sample.json"
RESOURCE_LIMIT = 500
OUTPUT_LIMIT = 200
MAPPING_LIMIT = 200
MAPPING_ATTRIBUTE_LIMIT = 200
TEMPLATE_FILE_SIZE_IN_BYTES_LIMIT = 1500000


class TemplateFragment:  # pylint: disable=too-many-instance-attributes
    def __init__(self, type_name, root=None):
        self.root = Path(root) if root else Path.cwd()
        self.fragment_dir = self.root / FRAGMENT_DIR
        self.type_name = type_name
        self.resource_limit = RESOURCE_LIMIT
        self.output_limit = OUTPUT_LIMIT
        self.mapping_limit = MAPPING_LIMIT
        self.mapping_attribute_limit = MAPPING_ATTRIBUTE_LIMIT
        self.template_file_size_in_bytes_limit = TEMPLATE_FILE_SIZE_IN_BYTES_LIMIT

        LOG.debug("Fragment directory: %s", self.fragment_dir)

    def generate_schema(self):
        raw_fragments = read_raw_fragments(self.fragment_dir)

        schema = {}
        properties = {}

        schema["typeName"] = self.type_name
        schema["description"] = "Schema for Module Fragment of type " + self.type_name
        schema["properties"] = properties
        schema["additionalProperties"] = True

        if "Parameters" in raw_fragments:
            properties["Parameters"] = self.__build_parameters(raw_fragments)
        properties["Resources"] = self.__build_resources(raw_fragments)

        self.__write_schema(schema)

        return schema

    def validate_fragments(self):
        """
        This method makes sure that the fragments adhere
            to the template fragment restrictions.
        Note: Fn::ImportValue was checked when loading the fragments
            since it can occur anywhere in the template.
        """
        raw_fragments = read_raw_fragments(self.fragment_dir)
        self.__validate_file_size_limit()
        self.__validate_resources(raw_fragments)
        self.__validate_parameters(raw_fragments)
        self.__validate_no_transforms_present(raw_fragments)
        self.__validate_outputs(raw_fragments)
        self.__validate_mappings(raw_fragments)
        print_cfn_lint_warnings(self.fragment_dir)

    def __validate_outputs(self, raw_fragments):
        self.__validate_no_exports_present(raw_fragments)
        self.__validate_output_limit(raw_fragments)

    @staticmethod
    def __validate_no_exports_present(raw_fragments):
        if "Outputs" in raw_fragments:
            for _output_name, output in raw_fragments["Outputs"].items():
                if "Export" in output:
                    raise FragmentValidationError(
                        "Template fragment cannot contain any Export. "
                        "Found an Export statement in Output: " + _output_name
                    )

    def __validate_output_limit(self, raw_fragments):
        if "Outputs" in raw_fragments:
            output_count = len(raw_fragments["Outputs"].items())
            if output_count > self.output_limit:
                raise FragmentValidationError(
                    "The Module template fragment has "
                    + str(output_count)
                    + " outputs but must not exceed the limit of "
                    + str(self.output_limit)
                    + " outputs"
                )

    def __validate_resources(self, raw_fragments):
        if "Resources" not in raw_fragments:
            raise FragmentValidationError(
                "A Module template fragment must have a Resources section"
            )
        self.__validate_resource_limit(raw_fragments)
        for _resource_name, resource in raw_fragments["Resources"].items():
            if "Type" in resource:
                self.__validate_no_nested_stacks(resource)
                self.__validate_no_macros(resource)
            elif "Name" in resource:
                self.__validate_no_include(resource)
                raise FragmentValidationError(
                    "Resource '" + _resource_name + "' is invalid"
                )
            else:
                raise FragmentValidationError(
                    "Resource '" + _resource_name + "' has neither Type nor Name"
                )

    @staticmethod
    def __validate_no_include(resource):
        if resource["Name"] == "AWS::Include":
            raise FragmentValidationError(
                "Template fragment can't use AWS::Include transform."
            )

    @staticmethod
    def __validate_no_macros(resource):
        if resource["Type"] == "AWS::CloudFormation::Macro":
            raise FragmentValidationError("Template fragment can't contain any macro.")

    @staticmethod
    def __validate_no_nested_stacks(resource):
        if resource["Type"] == "AWS::CloudFormation::Stack":
            raise FragmentValidationError(
                "Template fragment can't contain nested stack."
            )

    def __validate_resource_limit(self, raw_fragments):
        resource_count = len(raw_fragments["Resources"].items())
        if resource_count > self.resource_limit:
            raise FragmentValidationError(
                "The Module template fragment has "
                + str(resource_count)
                + " resources but must not exceed the limit of "
                + str(self.resource_limit)
                + " resources"
            )

    @staticmethod
    def __validate_parameters(raw_fragments):
        if "Parameters" in raw_fragments:
            for _parameter_name, parameter in raw_fragments["Parameters"].items():
                if "Type" not in parameter:
                    raise FragmentValidationError(
                        "Parameter '" + _parameter_name + "' must have a Type"
                    )

    @staticmethod
    def __validate_no_transforms_present(raw_fragments):
        if "transform" in raw_fragments or "Transform" in raw_fragments:
            raise FragmentValidationError(
                "Template fragment can't contain transform section."
            )
        if "Fn::Transform" in raw_fragments:
            raise FragmentValidationError(
                "Template fragment can't contain any transform."
            )

    def __validate_mappings(self, raw_fragments):
        self.__validate_mapping_limit(raw_fragments)
        self.__validate_mapping_attribute_limit(raw_fragments)

    def __validate_mapping_limit(self, raw_fragments):
        if "Mappings" in raw_fragments:
            mapping_count = len(raw_fragments["Mappings"].items())
            if mapping_count > self.mapping_limit:
                raise FragmentValidationError(
                    "The Module template fragment has "
                    + str(mapping_count)
                    + " mappings but must not exceed the limit of "
                    + str(self.output_limit)
                    + " mappings"
                )

    def __validate_mapping_attribute_limit(self, raw_fragments):
        if "Mappings" in raw_fragments:
            for _mapping_name, mapping in raw_fragments["Mappings"].items():
                attribute_count = len(mapping.items())
                if attribute_count > self.mapping_attribute_limit:
                    raise FragmentValidationError(
                        "The mapping "
                        + _mapping_name
                        + " has "
                        + str(attribute_count)
                        + " attributes but must not exceed the limit of "
                        + str(self.output_limit)
                        + " mapping attributes"
                    )

    def __validate_file_size_limit(self):
        total_size = get_template_file_size_in_bytes(self.fragment_dir)
        if total_size > self.template_file_size_in_bytes_limit:
            raise FragmentValidationError(
                "The total file size of the template"
                " fragments exceeds the CloudFormation Template size limit"
            )

    @staticmethod
    def __build_resources(raw_fragments):
        raw_resources = {}
        resources = {}
        for resource in raw_fragments["Resources"]:
            raw_resources[resource] = {
                "type": raw_fragments["Resources"][resource]["Type"]
            }
        resources_properties = {}
        for resource in raw_resources:
            type_object = {"type": "object", "properties": {}}
            type_object["properties"]["Type"] = {
                "type": "string",
                "const": raw_resources[resource]["type"],
            }
            type_object["properties"]["Properties"] = {"type": "object"}
            resources_properties[resource] = type_object
        resources["properties"] = resources_properties
        resources["type"] = "object"
        resources["additionalProperties"] = False
        return resources

    @staticmethod
    def __build_parameters(raw_fragments):
        raw_parameters = {}
        parameters = {}
        for param in raw_fragments["Parameters"]:
            param_type = raw_fragments["Parameters"][param]["Type"]

            description = raw_fragments["Parameters"][param].get("Description")
            raw_parameters[param] = {
                "type": param_type.lower(),
                "description": description,
            }
        parameter_properties = {}
        for raw_param in raw_parameters:
            description = raw_parameters[raw_param]["description"]
            type_name = "object"
            properties = {"Type": {"type": "string"}}
            required = ["Type"]
            parameter_properties[raw_param] = {
                "type": type_name,
                "properties": properties,
                "required": required,
            }
            if description is not None:
                parameter_properties[raw_param]["description"] = description
                properties["Description"] = {"type": "string"}
                required.append("Description")
        parameters["type"] = "object"
        parameters["properties"] = parameter_properties
        return parameters

    def __write_schema(self, schema):
        def _write(f):
            json.dump(schema, f, indent=4)
            f.write("\n")

        self._overwrite(self.root / SCHEMA_NAME, _write)

    def generate_sample_fragment(self):
        self._create_fragment_directory()
        sample_json = self.__get_sample_fragment_json()

        def _write(f):
            json.dump(sample_json, f, indent=4)
            f.write("\n")

        self._overwrite(self.fragment_dir / SAMPLE_FRAGMENT_OUTPUT, _write)

    @staticmethod
    def __get_sample_fragment_json():
        sample_json = resource_json(__name__, SAMPLE_FRAGMENT)
        return sample_json

    def _create_fragment_directory(self):
        if not os.path.exists(self.fragment_dir):
            os.mkdir(self.fragment_dir)
            print("Directory ", self.fragment_dir, " Created ")
        else:
            print("Directory ", self.fragment_dir, " already exists")

    @staticmethod
    def _overwrite(path, contents):
        LOG.debug("Overwriting '%s'", path)
        with path.open("w", encoding="utf-8") as f:
            if callable(contents):
                contents(f)
            else:
                f.write(contents)
