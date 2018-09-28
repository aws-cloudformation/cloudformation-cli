# fixture and parameter have the same name
# pylint: disable=redefined-outer-name
import json
from pathlib import Path

import pytest
from jsonschema import Draft6Validator
from jsonschema.exceptions import ValidationError


@pytest.fixture
def schema():
    basedir = Path(__file__).parent.parent
    awscommonschema = basedir / "examples" / "schema" / "aws.common.types.v1.json"
    with awscommonschema.open("r", encoding="utf-8") as f:
        resource_schema = json.load(f)
    return resource_schema


def test_arn_correct(schema):
    arn_config = schema["definitions"]["Arn"]
    validator = Draft6Validator(arn_config)

    validator.validate("arn:aws:rds:eu-west-1:123456789012:db:mysql-db")


def test_arn_wrong(schema):
    arn_config = schema["definitions"]["Arn"]
    validator = Draft6Validator(arn_config)

    with pytest.raises(ValidationError):
        validator.validate("arn:aws:rds:eu-west-1:1234")


def test_availbilityzone_correct(schema):
    availbilityzone_config = schema["definitions"]["AvailabilityZone"]
    validator = Draft6Validator(availbilityzone_config)

    validator.validate("us-wast-2b")


def test_availbilityzone_wrong(schema):
    availbilityzone_config = schema["definitions"]["AvailabilityZone"]
    validator = Draft6Validator(availbilityzone_config)

    with pytest.raises(ValidationError):
        validator.validate("us-west")


def test_tag_correct(schema):
    tag_config = schema["definitions"]["Tag"]
    validator = Draft6Validator(tag_config)

    validator.validate({"Key": "123abc", "Value": "123abc"})


def test_tag_wrong(schema):
    tag_config = schema["definitions"]["Tag"]
    validator = Draft6Validator(tag_config)

    with pytest.raises(ValidationError):
        validator.validate({"Key": "aws:123abc", "Value": "aws:123abc"})
