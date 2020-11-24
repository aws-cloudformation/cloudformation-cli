import os
from pathlib import Path
from unittest.mock import patch

import pytest

from rpdk.core.data_loaders import make_validator, resource_json
from rpdk.core.exceptions import FragmentValidationError
from rpdk.core.fragment.generator import TemplateFragment
from tests.utils import CONTENTS_UTF8

type_name = "AWS::ORG::MYTYPE::MODULE"
TIMEOUT_IN_SECONDS = 10

directory = os.path.dirname(__file__)

test_root = "build"


@pytest.fixture
def template_fragment():
    return TemplateFragment(type_name, test_root)


def test_schema_generator(template_fragment):
    fragment1 = os.path.join(directory, "../data/sample_fragments/sample.json")
    merged_fragment = template_fragment._load_fragment(fragment1)
    with patch.object(
        template_fragment, "_read_raw_fragments", return_value=merged_fragment
    ):
        schema = template_fragment.generate_schema()

    assert os.path.exists(test_root + "/schema.json")

    assert len(schema) == 4
    assert len(schema["properties"]) == 2
    assert "Parameters" in schema["properties"]
    assert "Resources" in schema["properties"]
    assert "S3Bucket" in schema["properties"]["Resources"]["properties"]
    assert (
        len(schema["properties"]["Resources"]["properties"]["S3Bucket"]["properties"])
        == 2
    )
    assert (
        schema["properties"]["Resources"]["properties"]["S3Bucket"]["properties"][
            "Properties"
        ]["type"]
        == "object"
    )
    __validate_against_meta_schema(schema)
    os.remove(test_root + "/schema.json")


def test_schema_generation_param_without_description(template_fragment):
    schema = __generate_schema("paramWithoutDescription.yaml", template_fragment)

    assert len(schema) == 4
    assert len(schema["properties"]) == 2
    assert "Parameters" in schema["properties"]
    assert (
        "Description"
        not in schema["properties"]["Parameters"]["properties"]["anInput"]["required"]
    )
    __validate_against_meta_schema(schema)
    os.remove(test_root + "/schema.json")


def test_schema_generation_param_type_aws_specific(template_fragment):
    schema = __generate_schema("aws-specific-parameter.json", template_fragment)

    assert len(schema) == 4
    assert len(schema["properties"]) == 2
    assert (
        schema["properties"]["Parameters"]["properties"]["VpcId"]["properties"]["Type"][
            "type"
        ]
        == "string"
    )
    __validate_against_meta_schema(schema)
    os.remove(test_root + "/schema.json")


def test_template_fragments_without_parameter_section(template_fragment):
    schema = __generate_schema(
        "template_without_parameter_section.json", template_fragment
    )

    assert len(schema) == 4
    assert schema["properties"] is not None
    assert schema["properties"]["Resources"] is not None
    __validate_against_meta_schema(schema)
    os.remove(test_root + "/schema.json")


def test_template_fragments_without_parameter_section_is_valid(template_fragment):
    __assert_validation_throws_no_error(
        "template_without_parameter_section.json", template_fragment
    )


def test_template_fragments_without_description(template_fragment):
    schema = __generate_schema("template_without_description.json", template_fragment)

    assert len(schema) == 4
    assert schema["properties"] is not None
    assert schema["description"] is not None
    assert schema["properties"].get("Resources") is not None
    assert schema["properties"].get("Parameters") is not None
    __validate_against_meta_schema(schema)
    os.remove(test_root + "/schema.json")


def test_template_fragment_with_empty_description(template_fragment):
    schema = __generate_schema(
        "template_with_empty_description.json", template_fragment
    )

    assert len(schema) == 4
    assert schema["properties"] is not None
    assert schema["description"] is not None
    assert schema["properties"].get("Resources") is not None
    assert schema["properties"].get("Parameters") is not None
    __validate_against_meta_schema(schema)
    os.remove(test_root + "/schema.json")


def __generate_schema(fragment_file_name, template_fragment):
    if not os.path.exists(test_root):
        os.mkdir(test_root)
    fragment = os.path.join(directory, "../data/sample_fragments/" + fragment_file_name)
    merged_fragment = template_fragment._load_fragment(fragment)
    with patch.object(
        template_fragment, "_read_raw_fragments", return_value=merged_fragment
    ):
        schema = template_fragment.generate_schema()
    return schema


def test_resolved_generated_schema_is_valid_against_metaschema(template_fragment):
    if not os.path.exists(test_root):
        os.mkdir(test_root)
    fragment1 = os.path.join(
        directory, "../data/sample_fragments/secureS3_resolved.json"
    )
    merged_fragment = template_fragment._load_fragment(fragment1)
    with patch.object(
        template_fragment, "_read_raw_fragments", return_value=merged_fragment
    ):
        schema = template_fragment.generate_schema()

    __validate_against_meta_schema(schema)
    assert os.path.exists(test_root + "/schema.json")
    os.remove(test_root + "/schema.json")


def __validate_against_meta_schema(schema):
    __make_resource_validator().validate(schema)


def test_generate_sample_fragment(template_fragment):
    if not os.path.exists(test_root):
        os.mkdir(test_root)
    sample_fragment_folder_path = test_root + "/fragments"
    sample_fragment_path = sample_fragment_folder_path + "/sample.json"
    if os.path.exists(sample_fragment_path):
        os.remove(sample_fragment_path)
        os.rmdir(sample_fragment_folder_path)
    assert not os.path.exists(sample_fragment_path)
    template_fragment.generate_sample_fragment()
    assert os.path.exists(sample_fragment_path)


def test_fragments_are_loaded_yaml_short(template_fragment):
    fragment = os.path.join(directory, "../data/sample_fragments/ec2_short.yaml")
    merged_fragment = template_fragment._load_fragment(fragment)
    assert len(merged_fragment) == 2
    assert len(merged_fragment["Resources"]) == 1
    assert "MyEC2Instance" in merged_fragment["Resources"]


def test_template_fragments_are_valid(template_fragment):
    __assert_validation_throws_no_error("sample.json", template_fragment)


def test_template_fragments_import_value(template_fragment):
    __assert_throws_validation_error(
        "import_value.json", template_fragment, "can't contain any Fn::ImportValue"
    )


def test_template_fragments_import_value_short(template_fragment):
    __assert_throws_validation_error(
        "import_short.yaml", template_fragment, "can't contain any Fn::ImportValue"
    )


def test_template_fragments_include_resource_level(template_fragment):
    __assert_throws_validation_error(
        "include.json", template_fragment, "can't use AWS::Include"
    )


def test_template_fragments_include_top_level(template_fragment):
    __assert_throws_validation_error(
        "top_level_include.json", template_fragment, "can't contain any transform"
    )


def test_template_fragments_invalid_transform(template_fragment):
    __assert_throws_validation_error(
        "invalid_transform.json",
        template_fragment,
        "Resource 'Fn::Transform' is invalid",
    )


def test_template_fragments_resource_without_type(template_fragment):
    __assert_throws_validation_error(
        "resource_without_type_or_name.json",
        template_fragment,
        "has neither Type nor Name",
    )


def test_template_fragments_macros(template_fragment):
    __assert_throws_validation_error(
        "macros.yaml", template_fragment, "can't contain any macro"
    )


def test_template_fragments_nested_stack(template_fragment):
    __assert_throws_validation_error(
        "nested_stack.json", template_fragment, "can't contain nested stack"
    )


def test_template_fragments_parameter_without_type(template_fragment):
    __assert_throws_validation_error(
        "parameter_without_type.json", template_fragment, "must have a Type"
    )


def test_template_fragments_transform(template_fragment):
    __assert_throws_validation_error(
        "transform.json", template_fragment, "can't contain transform section"
    )


def test_template_fragments_transform_section(template_fragment):
    __assert_throws_validation_error(
        "transform_section.json", template_fragment, "can't contain transform section"
    )


def test_template_fragments_without_resources(template_fragment):
    __assert_throws_validation_error(
        "noresources.json", template_fragment, "must have a Resources section"
    )


def test_template_fragments_with_json_syntax_error(template_fragment):
    __assert_throws_validation_error(
        "syntax_error.json", template_fragment, "line 15, column 24"
    )


def test_template_fragments_exports(template_fragment):
    __assert_throws_validation_error(
        "exports.json", template_fragment, "cannot contain any Export"
    )


def test_template_fragments_output_without_export_is_valid(template_fragment):
    __assert_validation_throws_no_error("output.json", template_fragment)


def test_template_exceeding_resource_limit(template_fragment):
    template_fragment.resource_limit = 2
    __assert_throws_validation_error(
        "fragment_three_resources.json",
        template_fragment,
        "has 3 resources but must not exceed the limit of 2",
    )


def test_template_exceeding_output_limit(template_fragment):
    template_fragment.output_limit = 2
    __assert_throws_validation_error(
        "fragment_three_outputs.json",
        template_fragment,
        "has 3 outputs but must not exceed the limit of 2",
    )


def test_template_exceeding_mapping_limit(template_fragment):
    template_fragment.mapping_limit = 2
    __assert_throws_validation_error(
        "fragment_three_mappings.json",
        template_fragment,
        "has 3 mappings but must not exceed the limit of 2",
    )


def test_template_exceeding_mapping_attribute_limit(template_fragment):
    template_fragment.mapping_attribute_limit = 2
    __assert_throws_validation_error(
        "fragment_mapping_with_three_attributes.json",
        template_fragment,
        "has 3 attributes but must not exceed the limit of 2",
    )


def test_template_mappings_dont_exceed_any_limit(template_fragment):
    __assert_validation_throws_no_error(
        "fragment_mapping_with_three_attributes.json", template_fragment
    )


def test_template_exceeding_file_size_limit(template_fragment):
    template_fragment.template_file_size_in_bytes_limit = 300
    __assert_throws_validation_error(
        "sample.json",
        template_fragment,
        "exceeds the CloudFormation Template size limit",
    )


def test_template_folder_with_multiple_fragment_files():
    template_fragment = TemplateFragment(
        type_name,
        os.path.join(directory, "../data/sample_fragments/test_multiple_files"),
    )
    with pytest.raises(FragmentValidationError) as validation_error:
        template_fragment.validate_fragments()
    assert "can only consist of a single template file" in str(validation_error.value)


def test_merge_fragments_ignores_unrelated_files():
    template_fragment = TemplateFragment(
        type_name, os.path.join(directory, "../data/sample_fragments/")
    )
    template_fragment.validate_fragments()


def __assert_validation_throws_no_error(template_file_name, template_fragment):
    with patch.object(
        template_fragment,
        "_get_fragment_file",
        return_value=os.path.join(
            directory, "../data/sample_fragments/" + template_file_name
        ),
    ):
        template_fragment.validate_fragments()


def __assert_throws_validation_error(
    template_file_name, template_fragment, expected_error_message_fragment
):
    with pytest.raises(FragmentValidationError) as validation_error:
        with patch.object(
            template_fragment,
            "_get_fragment_file",
            return_value=os.path.join(
                directory, "../data/sample_fragments/" + template_file_name
            ),
        ):
            template_fragment.validate_fragments()
    assert expected_error_message_fragment in str(validation_error.value)


def test_overwrite_doesnt_exist(template_fragment, tmpdir):
    path = Path(tmpdir.join("test")).resolve()

    template_fragment._overwrite(path, CONTENTS_UTF8)

    with path.open("r", encoding="utf-8") as f:
        assert f.read() == CONTENTS_UTF8


def __make_resource_validator(base_uri=None, timeout=TIMEOUT_IN_SECONDS):
    schema = resource_json(
        __name__,
        "../../src/rpdk/core/data/schema/provider.definition.schema.modules.v1.json",
    )
    return make_validator(schema, base_uri=base_uri)
