# Modeling Resource Providers for Use in AWS CloudFormation<a name="resource-type-model"></a>

The first step in creating a resource provider is *modeling* that resource, which involves crafting a schema that defines the resource, its properties, and their attributes\. When you initially create your resource provider project using the CloudFormation CLI `[init](resource-type-cli-init.md)` command, one of the files created is an example resource schema\. Use this schema file as a starting point for defining the shape and semantics of your resource provider\.

In order to be considered valid, your resource provider's schema must adhere to the [Resource Provider Definition Schema](https://github.com/aws-cloudformation/aws-cloudformation-rpdk/blob/master/src/rpdk/core/data/schema/provider.definition.schema.v1.json)\. This meta\-schema provides a means of validating your resource specification during resource development\.

The Resource Provider Definition Schema is a *meta\-schema* that extends [draft\-07](https://json-schema.org/draft-07/json-schema-release-notes.html) of the [JSON Schema](https://json-schema.org/)\. To simplify authoring resource specifications, the Resource Provider Definition Schema constrains the scope of the full JSON Schema standard in terms of how certain validations can be expressed, and encourages consistent modelling for all resource schemas\. \(For full details on how the Resource Provider Definition Schema differs from the full JSON schema, see [Divergence From JSON Schema](https://github.com/aws-cloudformation/aws-cloudformation-rpdk/blob/master/src/rpdk/core/data/schema/README.md#divergence-from-json-schema)\.\)

Once you have defined your resource schema, you can use the CloudFormation CLI ` [validate](resource-type-cli-validate.md)` command to verify that the resource schema is valid\.

In terms of testing, the resource schema also determines:
+ What unit test stubs are generated in your resource package, and what contract tests are appropriate to run for the resource\. When you run the CloudFormation CLI ` [generate](resource-type-cli-generate.md)` command, the CloudFormation CLI generates empty unit tests based on the properties of the resource and their attributes\.
+ Which contract tests are appropriate for CloudFormation CLI to run for your resources\. When you run the ` [test](resource-type-cli-test.md)` command, the CloudFormation CLI runs the appropriate contract tests, based on which handlers are included in your resource schema\.

## Defining Property Attributes<a name="resource-type-model-setting-properties"></a>

Certain properties of a resource may have special meaning when used in different contexts\. For example, a given resource property may be read\-only when read back for state changes, but can be specified when used as the target of a $ref from a related resource\. Because of this semantic difference in how this property metadata should be interpreted, certain property attributes are defined at the resource level, rather than at a property level\.

These attributes include:
+ `primaryIdentifier`
+ `additionalIdentifiers`
+ `createOnlyProperties`
+ `readOnlyProperties`
+ `writeOnlyProperties`

For reference information on resource schema elements, see [Resource Provider Schema](resource-type-schema.md)\.

## How to Define a Minimal Resource<a name="resource-type-howto-minimal"></a>

The example below displays a minimal resource provider definition\. In this case, the resource consists of a single optional property, `Name`, which is also specified as its primary \(and only\) identifier\.

Note that this resource schema would require a `handlers` section with the create, read, and update handlers specified in order for the resource to actually be provisioned within a CloudFormation account\.

```
{
    "typeName": "myORG::myService::myResource",
    "properties": {
        "Name": {
            "description": "The name of the resource.",
            "type": "string",
            "pattern": "^[a-zA-Z0-9_-]{0,64}$",
            "maxLength": 64
        }
    },
    "createOnlyProperties": [
        "/properties/Name"
    ],
    "identifiers": [
        [
            "/properties/Name"
        ]
    ],
    "additionalProperties": false
}
```
