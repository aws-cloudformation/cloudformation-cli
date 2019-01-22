FLATTENED_SCHEMA = {
    ("definitions", "location"): {
        "type": "object",
        "properties": {
            "country": {"type": "string"},
            "stateNumber": {"type": "integer"},
        },
    },
    ("properties", "coordinate", "items"): {
        "type": "object",
        "properties": {"lat": {"type": "number"}, "long": {"type": "number"}},
    },
    (): {
        "type": "object",
        "properties": {
            "state": {"$ref": ("definitions", "location")},
            "coordinates": {
                "type": "array",
                "items": {"$ref": ("properties", "coordinate", "items")},
            },
            "surroundingStates": {
                "type": "object",
                "patternProperties": {
                    "[A-Za-z0-9]{1,64}": {"$ref": ("definitions", "location")}
                },
            },
        },
    },
}
