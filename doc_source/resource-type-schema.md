# Resource Provider Schema<a name="resource-type-schema"></a>

In order to be considered valid, your resource provider's schema must adhere to the [Resource Provider Definition Schema](https://github.com/aws-cloudformation/aws-cloudformation-rpdk/blob/master/src/rpdk/core/data/schema/provider.definition.schema.v1.json)\. This meta\-schema provides a means of validating your resource specification during resource development\.

## Syntax<a name="resource-type-schema-syntax"></a>

Below is the structure for a typical resource provider schema\. For the complete meta\-schema definition, see the [Resource Provider Definition Schema](https://github.com/aws-cloudformation/aws-cloudformation-rpdk/blob/master/src/rpdk/core/data/schema/provider.definition.schema.v1.json) on [GitHub](https://github.com)\.

```
{
    "[typeName](#schema-properties-typeName)": "string",
    "[description](#schema-properties-description)": "string",
    "[sourceUrl](#schema-properties-sourceUrl)": "string",
    "[documentationUrl](#schema-properties-documentationurl)": "string",
    "[definitions](#schema-properties-definitions)": {
        "definitionName": {
          . . .
        }
    },
    "[properties](#schema-properties-properties)": {
         "[propertyName](#schema-properties-propertyname)": {
            "description": "string",
            "type": "string",
             . . .
        },

        },
    },
    "required": [
        "propertyName"
    ],
    "[readOnlyProperties](#schema-properties-readonlyproperties)": [
        "/properties/propertyName"
    ],
    "[writeOnlyProperties](#schema-properties-writeonlyproperties)": [
        "/properties/propertyName"
    ],
    "[primaryIdentifier](#schema-properties-primaryidentifier)": [
        "/properties/propertyName"
    ],
    "[createOnlyProperties](#schema-properties-createonlyproperties)": [
        "/properties/propertyName"
    ],
    "[deprecatedProperties](#schema-properties-deprecatedproperties)": [
        "/properties/propertyName"
    ],
    "[additionalIdentifiers](#schema-properties-additionalidentifiers)": [
        [
            "/properties/propertyName"
        ]
    ],
    "[handlers](#schema-properties-handlers)": {
        "[create](#schema-properties-handlers-create)": {
            "[permissions](#schema-properties-handlers-create-permissions)": [
                "permission"
            ]
        },
        "[read](#schema-properties-handlers-read)": {
            "[permissions](#schema-properties-handlers-read-permissions)": [
                "permission"
            ]
        },
        "[update](#schema-properties-handlers-update)": {
            "[permissions](#schema-properties-handlers-update-permissions)": [
                "permission"
            ]
        },
        "[delete](#schema-properties-handlers-delete)": {
            "[permissions](#schema-properties-handlers-delete-permissions)": [
                "permission"
            ]
        },
        "[list](#schema-properties-handlers-list)": {
            "[permissions](#schema-properties-handlers-list-permissions)": [
                "permission"
            ]
        }
    }
}
```

## Properties<a name="resource-type-schema-properties"></a>

`typeName`  <a name="schema-properties-typeName"></a>
The unique name for your resource\. Specifies a three\-part namespace for your resource, with a recommended pattern of `Organization::Service::Resource`\.
The following organization namespaces are reserved and cannot be used in your resource type names:
+ `Alexa`
+ `AMZN`
+ `Amazon`
+ `ASK`
+ `AWS`
+ `Custom`
+ `Dev`
 *Required*: Yes
 *Pattern*: `^[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}::[a-zA-Z0-9]{2,64}$`

`description`  <a name="schema-properties-description"></a>
A short description of the resource\. This will be displayed in the AWS CloudFormation console\.
*Required:* Yes

`sourceUrl`  <a name="schema-properties-sourceUrl"></a>
The URL of the source code for this resource, if public\.

`documentationUrl`  <a name="schema-properties-documentationurl"></a>
The URL of a page providing detailed documentation for this resource\.
While the resource schema itself should include complete and accurate property descriptions, the documentationURL property enables you to provide users with documentation that describes and explains the resource in more detail, including examples, use cases, and other detailed information\.

`definitions`  <a name="schema-properties-definitions"></a>
Use the `definitions` block to provide shared resource property schemas\.
It is considered a best practice is to use the `definitions` section to define schema elements that may be used at multiple points in your resource provider schema\. You can then use a JSON pointer to reference that element at the appropriate places in your resource provider schema\.

`properties`  <a name="schema-properties-properties"></a>
The properties of the resource\.
All properties of a resource must be expressed in the schema\. Arbitrary inputs are not allowed\. A resource must contain at least one property\.
Nested properties are not allowed\. Instead, define any nested properties in the `definitions` element, and use a `$ref` pointer to reference them in the desired property\.
*Required:* Yes
propertyName  <a name="schema-properties-propertyname"></a>
insertionOrder  <a name="schema-properties-properties-insertionorder"></a>
For properties of type `array`, set to `true` to specify that the order in which array items are specified must be honored, and that changing the order of the array will indicate a change in the property\.
The default is `false`\.
readOnly  <a name="schema-properties-properties-readonly"></a>
Reserved for CloudFormation use\.
writeOnly  <a name="schema-properties-properties-writeonly"></a>
Reserved for CloudFormation use\.
dependencies  <a name="schema-properties-properties-dependencies"></a>
Any properties that are required if this property is specified\.
patternProperties  <a name="schema-properties-properties-patternproperties"></a>
Use to specify a specification for key\-value pairs\.

```
"type": "object",
"propertyNames": {
   "format": "regex"
}
```
properties  <a name="schema-properties-properties-properties"></a>
*Minimum*: 1
patternProperties
*Pattern:* `^[A-Za-z0-9]{1,64}$`
Specifies a pattern that properties must match to be valid\.
allOf  <a name="schema-properties-properties-allof"></a>
The property must contain all of the data structures define here\.
Contains a single schema\. A list of schemas is not allowed\.
*Minimum*: 1
anyOf  <a name="schema-properties-properties-anyof"></a>
The property can contain any number of the data structures define here\.
Contains a single schema\. A list of schemas is not allowed\.
*Minimum*: 1
oneOf  <a name="schema-properties-properties-oneof"></a>
The property must contain only one of the data structures define here\.
Contains a single schema\. A list of schemas is not allowed\.
*Minimum*: 1
items  <a name="schema-properties-properties-items"></a>
For properties of type array, defines the data structure of each array item\.
Contains a single schema\. A list of schemas is not allowed\.
In addition, the following elements, defined in [draft\-07](https://json-schema.org/draft-07/json-schema-release-notes.html) of the [JSON Schema](https://json-schema.org/), are allowed in the `properties` object:
+ $ref
+ $comment
+ title
+ description
+ examples
+ default
+ multipleOf
+ maximum
+ exclusiveMaximum
+ minimum
+ exclusiveMinimum
+ exclusiveMinimum
+ minLength
+ pattern
+ maxItems
+ minItems
+ uniqueItems
+ contains
+ maxProperties
+ maxProperties
+ required
+ const
+ enum
+ type
+ format

remote  <a name="schema-properties-remote"></a>
Reserved for CloudFormation use\.

readOnlyProperties  <a name="schema-properties-readonlyproperties"></a>
Resource properties that can be returned by a `read` or `list` request, but cannot be set by the user\.
*Type*: List of JSON pointers

writeOnlyProperties  <a name="schema-properties-writeonlyproperties"></a>
Resource properties that can be specified by the user, but cannot be returned by a `read` or `list` request\. Write\-only properties are often used to contain passwords, secrets, or other sensitive data\.
*Type*: List of JSON pointers

createOnlyProperties  <a name="schema-properties-createonlyproperties"></a>
Resource properties that can be specified by the user only during resource creation\.
Any property not explicitly listed in the `createOnlyProperties` element can be specified by the user during a resource update operation\.
*Type*: List of JSON pointers

deprecatedProperties  <a name="schema-properties-deprecatedproperties"></a>
Resource properties that have been deprecated by the underlying service provider\. These properties are still accepted in create and update operations\. However they may be ignored, or converted to a consistent model on application\. Deprecated properties are not guaranteed to be returned by read operations\.
*Type*: List of JSON pointers

primaryIdentifier  <a name="schema-properties-primaryidentifier"></a>
The uniquely identifier for an instance of this resource provider\. An identifier is a non\-zero\-length list of JSON pointers to properties that form a single key\. An identifier can be a single or multiple properties to support composite\-key identifiers\.
*Type*: List of JSON pointers
*Required:* Yes

additionalIdentifiers  <a name="schema-properties-additionalidentifiers"></a>
An optional list of supplementary identifiers, each of which uniquely identifies an instance of this resource provider\. An identifier is a non\-zero\-length list of JSON pointers to properties that form a single key\. An identifier can be a single property, or multiple properties to construct composite\-key identifiers\.
*Type*: List of JSON pointers
*Minimum*: 1

handlers  <a name="schema-properties-handlers"></a>
Specifies the provisioning operations which can be performed on this resource provider\. The handlers specified determine what provisioning actions CloudFormation takes with respect to the resource during various stack operations\.
+ If the resource provider does not contain `create`, `read`, and `delete` handlers, CloudFormation cannot actually provision the resource\.
+ If the resource provider does not contain an `update` handler, CloudFormation cannot update the resource during stack update operations, and will instead replace it\.
If your resource type calls AWS APIs in any of its handlers, you must create an *[IAM execution role](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html)* that includes the necessary permissions to call those AWS APIs, and provision that execution role in your account\. For more information, see [Accessing AWS APIs from a Resource Type](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-develop.html#resource-type-develop-executionrole)\.
create  <a name="schema-properties-handlers-create"></a>
permissions  <a name="schema-properties-handlers-create-permissions"></a>
A string array that specifies the AWS permissions needed to invoke the create handler\.
You must specify at least one permission for each handler\.
`Required`: Yes
read  <a name="schema-properties-handlers-read"></a>
permissions  <a name="schema-properties-handlers-read-permissions"></a>
A string array that specifies the AWS permissions needed to invoke the read handler\.
You must specify at least one permission for each handler\.
`Required`: Yes
update  <a name="schema-properties-handlers-update"></a>
permissions  <a name="schema-properties-handlers-update-permissions"></a>
A string array that specifies the AWS permissions needed to invoke the update handler\.
You must specify at least one permission for each handler\.
`Required`: Yes
delete  <a name="schema-properties-handlers-delete"></a>
permissions  <a name="schema-properties-handlers-delete-permissions"></a>
A string array that specifies the AWS permissions needed to invoke the delete handler\.
You must specify at least one permission for each handler\.
`Required`: Yes
list  <a name="schema-properties-handlers-list"></a>
The `list` handler must at least return the resource's primary identifier\.
permissions  <a name="schema-properties-handlers-list-permissions"></a>
A string array that specifies the AWS permissions needed to invoke the list handler\.
You must specify at least one permission for each handler\.
`Required`: Yes

allOf  <a name="schema-properties-allof"></a>
The resource must contain all of the data structures defined here\.
*Minimum*: 1

anyOf  <a name="schema-properties-anyof"></a>
The resource can contain any number of the data structures define here\.
*Minimum*: 1

oneOf  <a name="schema-properties-oneof"></a>
The resource must contain only one of the data structures define here\.
*Minimum*: 1

In addition, the following element, defined in [draft\-07](https://json-schema.org/draft-07/json-schema-release-notes.html) of the [JSON Schema](https://json-schema.org/), is allowed:
+ required

## How to Specify a Property as Dependent on Another<a name="resource-type-howto-dependencies"></a>

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

## How to Define Nested Properties<a name="resource-type-howto-nested-properties"></a>

It is considered a best practice is to use the `definitions` section to define schema elements that may be used at multiple points in your resource provider schema\. You can then use a JSON pointer to reference that element at the appropriate places in your resource provider schema\.

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

## Advanced: How to Encapsulate Complex Logic<a name="resource-type-howto-logic"></a>

Use the `allOf`, `oneOf`, or `anyOf` elements to encapsulate complex logic in your resource provider schema\.

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
