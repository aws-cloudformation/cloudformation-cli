# pylint:disable=line-too-long
CIRCULAR_REFERENCE_SCHEMA = {
    "#": {
        "resourceType": "AWS::Circular::Reference",
        "definitions": {
            "TestA": {"$ref": "#/definitions/TestB"},
            "TestB": {
                "type": "object",
                "properties": {"SubTestB": {"$ref": "#/definitions/TestB"}},
            },
        },
        "properties": {"Test": {"$ref": "#/definitions/TestB"}},
        "additionalProperties": False,
    },
    "#/definitions/TestB": {
        "type": "object",
        "properties": {"SubTestB": {"$ref": "#/definitions/TestB"}},
    },
}
