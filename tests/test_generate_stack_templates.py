import json
import os
import re
import shutil
import uuid
from pathlib import Path
from unittest.mock import ANY, patch

import pytest

from rpdk.core.generate_stack_templates import (
    CONTRACT_TEST_DEPENDENCY_FILE_NAME,
    CONTRACT_TEST_FOLDER,
    StackTemplateGenerator,
)


@pytest.fixture(name="stack_template_generator")
def setup_fixture(tmp_path):
    root_path = tmp_path
    type_name = "AWS::Example::Resource"
    stack_template_config = {
        "root_folder_path": root_path / "stack-templates",
        "target_folder_path": root_path / "stack-templates" / "target",
        "dependency_file_name": CONTRACT_TEST_DEPENDENCY_FILE_NAME,
        "file_prefix": "stack-template-",
        "file_generation_enabled": True,
    }
    contract_test_file_names = ["inputs_1.json", "inputs_2.json"]
    contract_test_folder = root_path / CONTRACT_TEST_FOLDER
    contract_test_folder.mkdir(parents=True, exist_ok=True)
    # Create a dummy JSON file in the contract_test_folder directory
    create_dummy_json_file(contract_test_folder, "inputs_1.json")
    create_dummy_json_file(contract_test_folder, "inputs_2.json")
    (contract_test_folder / CONTRACT_TEST_DEPENDENCY_FILE_NAME).touch()

    return StackTemplateGenerator(
        type_name,
        stack_template_config,
        contract_test_file_names,
        root_path,
    )


def create_dummy_json_file(directory: Path, file_name: str):
    """Create a dummy JSON file in the given directory."""
    dummy_json_file = directory / file_name
    dummy_data = {
        "CreateInputs": {
            "Property1": "Value1",
            "Property2": "Value1",
        }
    }
    with dummy_json_file.open("w") as f:
        json.dump(dummy_data, f)


def create_folder(folder: Path):
    if os.path.exists(folder):
        shutil.rmtree(folder)
    folder.mkdir()


def test_is_file_generation_enabled(stack_template_generator):
    assert stack_template_generator.file_generation_enabled is True


def test_contract_test_folder_exists(stack_template_generator):
    assert stack_template_generator.contract_test_folder_exists() is True


def test_generate_stack_template_files(stack_template_generator, tmp_path):
    stack_template_generator.generate_stack_templates()

    stack_template_root_path = stack_template_generator.stack_template_root_folder_path
    stack_template_folder_path = (
        stack_template_generator.target_stack_template_folder_path
    )
    assert stack_template_root_path.exists()
    assert stack_template_folder_path.exists()

    template_files = list(
        stack_template_folder_path.glob(f"{stack_template_generator.file_prefix}*")
    )
    assert len(template_files) == 2
    template_files.sort()
    assert template_files[0].name == f"{stack_template_generator.file_prefix}1_001.yaml"
    assert template_files[1].name == f"{stack_template_generator.file_prefix}2_001.yaml"

    bootstrap_file = (
        stack_template_root_path
        / stack_template_generator.stack_template_dependency_file_name
    )
    assert bootstrap_file.exists()


@pytest.mark.usefixtures("stack_template_generator")
def test_clean_and_create_template_folder(stack_template_generator, tmp_path):
    template_root_path = stack_template_generator.stack_template_root_folder_path
    template_folder_path = stack_template_generator.target_stack_template_folder_path
    template_root_path.mkdir()
    (template_root_path / "existing_file.txt").touch()
    stack_template_generator.clean_and_create_stack_template_folder(
        template_root_path, template_folder_path
    )
    assert template_root_path.exists()
    assert not list(template_folder_path.glob("*"))
    assert template_folder_path.exists()


def test_create_template_bootstrap(stack_template_generator, tmp_path):
    contract_test_folder = tmp_path / CONTRACT_TEST_FOLDER
    create_folder(contract_test_folder)
    (contract_test_folder / CONTRACT_TEST_DEPENDENCY_FILE_NAME).touch()

    template_root_path = stack_template_generator.stack_template_root_folder_path
    create_folder(template_root_path)

    stack_template_generator.create_stack_template_bootstrap(
        contract_test_folder, template_root_path
    )

    bootstrap_file = (
        template_root_path
        / stack_template_generator.stack_template_dependency_file_name
    )
    assert bootstrap_file.exists()


@patch("rpdk.core.generate_stack_templates.yaml.dump")
def test_create_template_file(mock_yaml_dump, stack_template_generator, tmp_path):
    contract_test_folder = tmp_path / CONTRACT_TEST_FOLDER
    create_folder(contract_test_folder)
    contract_test_file = contract_test_folder / "inputs_1.json"
    contract_test_data = {
        "CreateInputs": {
            "Property1": "Value1",
            "Property2": "{{test123}}",
            "Property3": {"Nested": "{{partition}}"},
            "Property4": ["{{region}}", "Value2"],
            "Property5": "{{uuid}}",
            "Property6": "{{account}}",
        }
    }
    with contract_test_file.open("w") as f:
        json.dump(contract_test_data, f)

    template_folder_path = stack_template_generator.target_stack_template_folder_path
    template_folder_path.mkdir(parents=True, exist_ok=True)

    stack_template_generator.create_stack_template_file(
        "AWS::Example::Resource",
        contract_test_file,
        template_folder_path,
        stack_template_generator.file_prefix,
        1,
    )

    expected_template_data = {
        "Description": "Template for AWS::Example::Resource",
        "Resources": {
            "Resource": {
                "Type": "AWS::Example::Resource",
                "Properties": {
                    "Property1": "Value1",
                    "Property2": {"Fn::ImportValue": ANY},
                    "Property3": {"Nested": {"Fn::Sub": "${AWS::Partition}"}},
                    "Property4": [{"Fn::Sub": "${AWS::Region}"}, "Value2"],
                    "Property5": ANY,
                    "Property6": {"Fn::Sub": "${AWS::AccountId}"},
                },
            }
        },
    }
    args, kwargs = mock_yaml_dump.call_args
    assert args[0] == expected_template_data
    assert kwargs
    # Assert UUID generation
    replaced_properties = args[0]["Resources"]["Resource"]["Properties"]
    assert isinstance(replaced_properties["Property5"], str)
    assert len(replaced_properties["Property5"]) == 36  # Standard UUID length
    assert re.match(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        replaced_properties["Property5"],
    )

    # Assert the generated UUID is a valid UUID
    generated_uuid = replaced_properties["Property5"]
    assert uuid.UUID(generated_uuid)


def test_replace_dynamic_values(stack_template_generator):
    properties = {
        "Property1": "Value1",
        "Property2": "{{uuid}}",
        "Property3": {"Nested": "{{partition}}"},
        "Property4": ["{{region}}", "Value2"],
        "Property5": [{"Key": "{{uuid}}"}],
        "Property6": "{{account}}",
        "Property7": "prefix-{{uuid}}-sufix",
        "Property8": "{{value8}}",
    }
    replaced_properties = stack_template_generator.replace_dynamic_values(properties)
    assert replaced_properties["Property1"] == "Value1"
    assert isinstance(replaced_properties["Property2"], str)
    assert len(replaced_properties["Property2"]) == 36
    assert re.match(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        replaced_properties["Property2"],
    )
    assert replaced_properties["Property3"]["Nested"] == {
        "Fn::Sub": "${AWS::Partition}"
    }
    assert replaced_properties["Property4"][0] == {"Fn::Sub": "${AWS::Region}"}
    assert replaced_properties["Property4"][1] == "Value2"
    assert replaced_properties["Property6"] == {"Fn::Sub": "${AWS::AccountId}"}
    property7_value = replaced_properties["Property7"]
    # Assert the replaced value
    assert isinstance(property7_value, str)
    assert "prefix-" in property7_value
    assert "-sufix" in property7_value
    # Extract the UUID part
    property7_value = property7_value.replace("prefix-", "").replace("-sufix", "")
    # Assert the UUID format
    assert len(property7_value) == 36  # Standard UUID length
    assert re.match(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", property7_value
    )
    # Assert the UUID is a valid UUID
    assert uuid.UUID(property7_value)
    assert replaced_properties["Property8"] == {"Fn::ImportValue": "value8"}
