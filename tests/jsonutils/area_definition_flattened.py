AREA_DEFINITION_FLATTENED = {
    (): {
        "typeName": "AWS::geography::areaDescription",
        "definitions": {
            "location": {
                "type": "object",
                "properties": {
                    "country": {"type": "string"},
                    "boundary": {"$ref": "#/definitions/boundary"},
                },
            },
            "coordinate": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                },
            },
            "boundary": {
                "type": "object",
                "properties": {
                    "box": {
                        "type": "object",
                        "properties": {
                            "north": {"$ref": "#/definitions/coordinate"},
                            "south": {"$ref": "#/definitions/coordinate"},
                            "east": {"$ref": "#/definitions/coordinate"},
                            "west": {"$ref": "#/definitions/coordinate"},
                        },
                    },
                    "otherPoints": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/coordinate"},
                        "uniqueItems": True,
                    },
                },
            },
            "areaId": {"type": "string"},
        },
        "properties": {
            "areaName": {"type": "string"},
            "areaId": {"type": "string"},
            "location": {"$ref": ("definitions", "location")},
            "city": {"$ref": ("properties", "city")},
        },
    },
    ("definitions", "location"): {
        "type": "object",
        "properties": {
            "country": {"type": "string"},
            "boundary": {"$ref": ("definitions", "boundary")},
        },
    },
    ("definitions", "boundary"): {
        "type": "object",
        "properties": {
            "box": {"$ref": ("definitions", "boundary", "properties", "box")},
            "otherPoints": {
                "type": "array",
                "items": {"$ref": ("definitions", "coordinate")},
                "uniqueItems": True,
            },
        },
    },
    ("definitions", "boundary", "properties", "box"): {
        "type": "object",
        "properties": {
            "north": {"$ref": ("definitions", "coordinate")},
            "south": {"$ref": ("definitions", "coordinate")},
            "east": {"$ref": ("definitions", "coordinate")},
            "west": {"$ref": ("definitions", "coordinate")},
        },
    },
    ("definitions", "coordinate"): {
        "type": "object",
        "properties": {"latitude": {"type": "number"}, "longitude": {"type": "number"}},
    },
    ("properties", "city"): {
        "type": "object",
        "properties": {
            "cityName": {"type": "string"},
            "neighborhoods": {
                "type": "array",
                "items": {
                    "type": "object",
                    "patternProperties": {
                        "[A-Za-z0-9]{1,64}": {
                            "$ref": (
                                "properties",
                                "city",
                                "properties",
                                "neighborhoods",
                                "items",
                                "patternProperties",
                                "[A-Za-z0-9]{1,64}",
                            )
                        }
                    },
                    "insertionOrder": True,
                },
            },
        },
    },
    (
        "properties",
        "city",
        "properties",
        "neighborhoods",
        "items",
        "patternProperties",
        "[A-Za-z0-9]{1,64}",
    ): {
        "type": "object",
        "properties": {
            "street": {"type": "string"},
            "charter": {"type": "object"},
            "houses": {
                "type": "object",
                "patternProperties": {"[A-Za-z0-9]{1,64}": {"type": "number"}},
            },
        },
    },
}
