# pylint:disable=line-too-long
NORMALIZED_SCHEMA = {
    "#": {
        "resourceType": "AWS::Geography::AreaDescription",
        "type": "object",
        "definitions": {
            "Location": {
                "type": "object",
                "properties": {
                    "Country": {"type": "string"},
                    "Boundary": {"$ref": "#/definitions/Boundary"},
                },
            },
            "Coordinate": {
                "type": "object",
                "properties": {
                    "Latitude": {"type": "number"},
                    "Longitude": {"type": "number"},
                },
            },
            "Boundary": {
                "type": "object",
                "properties": {
                    "Box": {"$ref": "#/definitions/Boundary/~properties/Box"},
                    "OtherPoints": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/Coordinate"},
                        "uniqueItems": True,
                    },
                },
            },
            "AreaId": {"type": "string"},
        },
        "properties": {
            "AreaName": {"type": "string"},
            "AreaId": {"type": "string"},
            "Location": {"$ref": "#/definitions/Location"},
            "City": {"$ref": "#/~properties/City"},
        },
        "additionalProperties": False,
    },
    "#/definitions/Location": {
        "type": "object",
        "properties": {
            "Country": {"type": "string"},
            "Boundary": {"$ref": "#/definitions/Boundary"},
        },
    },
    "#/definitions/Boundary": {
        "type": "object",
        "properties": {
            "Box": {"$ref": "#/definitions/Boundary/~properties/Box"},
            "OtherPoints": {
                "type": "array",
                "items": {"$ref": "#/definitions/Coordinate"},
                "uniqueItems": True,
            },
        },
    },
    "#/definitions/Boundary/~properties/Box": {
        "type": "object",
        "properties": {
            "North": {"$ref": "#/definitions/Coordinate"},
            "South": {"$ref": "#/definitions/Coordinate"},
            "East": {"$ref": "#/definitions/Coordinate"},
            "West": {"$ref": "#/definitions/Coordinate"},
        },
    },
    "#/definitions/Coordinate": {
        "type": "object",
        "properties": {"Latitude": {"type": "number"}, "Longitude": {"type": "number"}},
    },
    "#/~properties/City": {
        "type": "object",
        "properties": {
            "CityName": {"type": "string"},
            "Neighborhoods": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": {
                        "$ref": "#/~properties/City/~properties/Neighborhoods/~items/~additionalProperties"  # noqa: B950
                    },
                    "insertionOrder": True,
                },
            },
        },
    },
    "#/~properties/City/~properties/Neighborhoods/~items/~additionalProperties": {
        "type": "object",
        "properties": {
            "Street": {"type": "string"},
            "Charter": True,
            "Houses": {"type": "object", "additionalProperties": {"type": "number"}},
        },
    },
}
