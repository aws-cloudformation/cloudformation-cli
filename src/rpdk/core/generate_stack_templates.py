import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

import yaml

CONTRACT_TEST_FOLDER = "contract-tests-artifacts"
CONTRACT_TEST_INPUT_PREFIX = "inputs_*"
CONTRACT_TEST_DEPENDENCY_FILE_NAME = "dependencies.yml"
FILE_GENERATION_ENABLED = "file_generation_enabled"
TYPE_NAME = "typeName"
CONTRACT_TEST_FILE_NAMES = "contract_test_file_names"
INPUT1_FILE_NAME = "inputs_1.json"
FN_SUB = "Fn::Sub"
FN_IMPORT_VALUE = "Fn::ImportValue"
UUID = "uuid"
DYNAMIC_VALUES_MAP = {
    "region": "${AWS::Region}",
    "partition": "${AWS::Partition}",
    "account": "${AWS::AccountId}",
}


class StackTemplateGenerator:
    def __init__(
        self,
        type_name: str,
        stack_template_config: dict,
        contract_test_file_names: list,
        root=None,
    ):
        self.root = Path(root) if root else Path.cwd()
        self.stack_template_config = stack_template_config
        self.type_name = type_name
        self.contract_test_file_names = contract_test_file_names

    @property
    def file_generation_enabled(self):
        return self.stack_template_config["file_generation_enabled"]

    @property
    def file_prefix(self):
        return self.stack_template_config["file_prefix"]

    @property
    def stack_template_root_folder_path(self):
        return self.stack_template_config["root_folder_path"]

    @property
    def target_stack_template_folder_path(self):
        return self.stack_template_config["target_folder_path"]

    @property
    def stack_template_dependency_file_name(self):
        return self.stack_template_config["dependency_file_name"]

    def generate_stack_templates(self) -> None:
        """
        Generate stack_template files based on the contract test input files.

        This method checks if file generation is enabled and if the target contract test folder exists.
        If both conditions are met, it creates the stack_template folder, copies the contract test dependencies,
        and generates stack_template files for each contract test input file up to the specified count.
        """
        if not self.file_generation_enabled or not self.contract_test_folder_exists():
            return
        self._setup_stack_template_environment()
        self._generate_stack_template_files()

    def contract_test_folder_exists(self) -> bool:
        return Path(self.target_contract_test_folder_path).exists()

    def _setup_stack_template_environment(self) -> None:
        stack_template_root = Path(self.stack_template_root_folder_path)
        stack_template_folder = Path(self.target_stack_template_folder_path)
        self.clean_and_create_stack_template_folder(
            stack_template_root, stack_template_folder
        )
        self.create_stack_template_bootstrap(
            Path(self.target_contract_test_folder_path), stack_template_root
        )

    def _generate_stack_template_files(self) -> None:
        resource_name = self.type_name
        stack_template_folder = Path(self.target_stack_template_folder_path)
        contract_test_files = self._get_sorted_contract_test_files()
        for count, ct_file in enumerate(contract_test_files, start=1):
            self.create_stack_template_file(
                resource_name, ct_file, stack_template_folder, self.file_prefix, count
            )

    def _get_sorted_contract_test_files(self) -> list:
        contract_test_folder = Path(self.target_contract_test_folder_path)
        contract_test_files = [
            file
            for file in contract_test_folder.glob(CONTRACT_TEST_INPUT_PREFIX)
            if file.is_file() and file.name in self.contract_test_file_names
        ]
        return sorted(contract_test_files)

    def clean_and_create_stack_template_folder(
        self, stack_template: Path, stack_template_folder: Path
    ) -> None:
        """
        Clean and create the stack_template folder.

        This method removes the existing stack_template root folder and creates a new stack_template folder.

        Args:
            stack_template (Path): The path to the stack_template root folder.
            stack_template_folder (Path): The path to the stack_template folder.
        """
        stack_template_folder.mkdir(parents=True, exist_ok=True)

    def create_stack_template_bootstrap(
        self, file_location: Path, stack_template: Path
    ) -> None:
        """
        Copy the contract test dependencies to the stack_template root folder.

        This method copies the contract test dependency file to the stack_template root folder
        as the stack_template bootstrap file.

        Args:
            file_location (Path): The path to the contract test folder.
            stack_template (Path): The path to the stack_template root folder.
        """
        dependencies_file = file_location / CONTRACT_TEST_DEPENDENCY_FILE_NAME
        bootstrap_file = stack_template / self.stack_template_dependency_file_name
        if dependencies_file.exists():
            shutil.copy(str(dependencies_file), str(bootstrap_file))

    def create_stack_template_file(
        self,
        resource_type: str,
        ct_file: Path,
        stack_template_folder: Path,
        stack_template_file_name_prefix: str,
        count: int,
    ) -> None:
        """
        Create a stack_template file based on the contract test input file.

        This method generates a stack_template file in YAML format based on the provided contract test input file.
        The stack_template file contains the resource configuration with dynamic values replaced.

        Args:
            resource_type (str): The type of the resource being tested.
            ct_file (Path): The path to the contract test input file.
            stack_template_folder (Path): The path to the stack_template folder.
            stack_template_file_name_prefix (str): The prefix for the stack_template file name.
            count (int): The count of the stack_template file being generated.
        """
        with ct_file.open("r") as f:
            json_data = json.load(f)
        resource_name = resource_type.split("::")[2]
        stack_template_data = {
            "Description": f"Template for {resource_type}",
            "Resources": {
                f"{resource_name}": {
                    "Type": resource_type,
                    "Properties": self.replace_dynamic_values(
                        json_data["CreateInputs"]
                    ),
                }
            },
        }
        stack_template_file_name = f"{stack_template_file_name_prefix}{count}_001.yaml"
        stack_template_file_path = stack_template_folder / stack_template_file_name

        with stack_template_file_path.open("w") as stack_template_file:
            yaml.dump(stack_template_data, stack_template_file, indent=2)

    def replace_dynamic_values(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replace dynamic values in the resource properties.

        This method recursively replaces dynamic values in the resource properties dictionary.
        It handles nested dictionaries, lists, and strings with dynamic value placeholders.

        Args:
            properties (Dict[str, Any]): The resource properties dictionary.

        Returns:
            Dict[str, Any]: The resource properties dictionary with dynamic values replaced.
        """
        for key, value in properties.items():
            if isinstance(value, dict):
                properties[key] = self.replace_dynamic_values(value)
            elif isinstance(value, list):
                properties[key] = [self._replace_dynamic_value(item) for item in value]
            else:
                return_value = self._replace_dynamic_value(value)
                properties[key] = return_value
        return properties

    def _replace_dynamic_value(self, original_value: Any) -> Any:
        """
        Replace a dynamic value with its corresponding value.

        This method replaces dynamic value placeholders in a string with their corresponding values.
        It handles UUID generation, partition replacement, and Fn::ImportValue function.

        Args:
            original_value (Any): The value to be replaced.

        Returns:
            Any: The replaced value.
        """
        pattern = r"\{\{(.*?)\}\}"

        def replace_token(match):
            token = match.group(1)
            if UUID in token:
                return str(uuid4())
            if token in DYNAMIC_VALUES_MAP:
                return DYNAMIC_VALUES_MAP[token]
            return f'{{"{FN_IMPORT_VALUE}": "{token.strip()}"}}'

        replaced_value = re.sub(pattern, replace_token, str(original_value))

        if any(value in replaced_value for value in DYNAMIC_VALUES_MAP.values()):
            replaced_value = {FN_SUB: replaced_value}
        if FN_IMPORT_VALUE in replaced_value:
            replaced_value = json.loads(replaced_value)
        return replaced_value

    @property
    def target_contract_test_folder_path(self):
        return self.root / CONTRACT_TEST_FOLDER
