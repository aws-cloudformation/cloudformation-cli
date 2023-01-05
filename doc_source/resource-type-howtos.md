# Patterns for modeling your resource types<a name="resource-type-howtos"></a>

Use the following patterns to model the data structures of your resource types using the Resource Provider Schema\.

## How to specify a property as dependent on another<a name="resource-type-howto-dependencies"></a>

Use the `dependencies` element to specify if a property is required in order for another property to be specified\. In the following example, if the user specifies a value for the `ResponseCode` property, they must also specify a value for `ResponsePagePath`, and vice versa\. \(Note that, as a best practice, this is also called out in the `description` of each property\.\)

```
"properties": {
"CustomErrorResponse": {
    "additionalProperties": false,
    "dependencies": {
        "ResponseCode": [
            "ResponsePagePath"
        ],
        "ResponsePagePath": [
            "ResponseCode"
        ]
    },
    "properties": {
        "ResponseCode": {
            "description": "The HTTP status code that you want CloudFront to return to the viewer along with the custom error page. If you specify a value for ResponseCode, you must also specify a value for ResponsePagePath.",
            "type": "integer"
        },
        "ResponsePagePath": {
            "description": "The path to the custom error page that you want CloudFront to return to a viewer when your origin returns the HTTP status code specified by ErrorCode. If you specify a value for ResponsePagePath, you must also specify a value for ResponseCode.",
            "type": "string"
        }
        . . .
    },
    "type": "object"
},
},
. . .
```

## How to define nested properties<a name="resource-type-howto-nested-properties"></a>

It is considered a best practice is to use the `definitions` section to define schema elements that may be used at multiple points in your resource type schema\. You can then use a JSON pointer to reference that element at the appropriate places in your resource type schema\.

For example, define the reused element in the `definitions` section:

```
"definitions": {
    "AccountId": {
        "pattern": "^[0-9]{12}$",
        "type": "string"
    },
    . . .
},
. . .
```

And then reference that definition where appropriate:

```
"AwsAccountNumber": {
    "description": "An AWS account that is included in the TrustedSigners complex type for this distribution.",
    "$ref": "#/definitions/AccountId"
},
    . . .
```

## Advanced: How to encapsulate complex logic<a name="resource-type-howto-logic"></a>

Use the `allOf`, `oneOf`, or `anyOf` elements to encapsulate complex logic in your resource type schema\.

In the example below, if `whitelist` is specified for the Forward property in your resource, then the `WhitelistedNames` property must also be specified\.

```
"properties": {
"Cookies": {
    "oneOf": [
        {
            "additionalProperties": false,
            "properties": {
               "Forward": {
                    "description": "Specifies which cookies to forward to the origin for this cache behavior.",
                    "enum": [
                        "all",
                        "none"
                    ],
                    "type": "string"
                }
            },
            "required": [
                "Forward"
            ]
        },
        {
            "additionalProperties": false,
            "properties": {
                "Forward": {
                    "description": "Specifies which cookies to forward to the origin for this cache behavior.",
                    "enum": [
                        "whitelist"
                    ],
                    "type": "string"
                },
                "WhitelistedNames": {
                    "description": "Required if you specify whitelist for the value of Forward.",
                    "items": {
                       "type": "string"
                    },
                    "minItems": 1,
                    "type": "array"
                }
            },
            "required": [
                "Forward",
                "WhitelistedNames"
            ]
        }
    ,
    type": "object"
},
},
. . .
```
