# Modeling resource types for use in AWS CloudFormation<a name="resource-type-model"></a>

The first step in creating a resource type is *modeling* that resource, which involves crafting a schema that defines the resource, its properties, and their attributes\. When you initially create your resource type project using the CloudFormation CLI `init` command, one of the files created is an example resource schema\. Use this schema file as a starting point for defining the shape and semantics of your resource type\.

**Note**  
When naming your extension, we recommend that you don't use the following namespaces: `aws`, `amzn`, `alexa`, `amazon`, `awsquickstart`\. CloudFormation doesn't block private registration using `cfn submit` for types whose names include these namespaces, but you won't be able to publish these types\.

In order to be considered valid, your resource type's schema must adhere to the [Resource type definition schema](https://github.com/aws-cloudformation/aws-cloudformation-rpdk/blob/master/src/rpdk/core/data/schema/provider.definition.schema.v1.json)\. This meta\-schema provides a means of validating your resource specification during resource development\.

The Resource Type Definition Schema is a *meta\-schema* that extends [draft\-07](https://json-schema.org/draft-07/json-schema-release-notes.html) of the [JSON Schema](https://json-schema.org/)\. To simplify authoring resource specifications, the Resource Type Definition Schema constrains the scope of the full JSON Schema standard in terms of how certain validations can be expressed, and encourages consistent modelling for all resource schemas\. \(For full details on how the Resource Type Definition Schema differs from the full JSON schema, see [Divergence From JSON Schema](https://github.com/aws-cloudformation/aws-cloudformation-resource-schema/blob/master/README.md#divergence-from-json-schema)\.\)

Once you have defined your resource schema, you can use the CloudFormation CLI ` validate` command to verify that the resource schema is valid\.

In terms of testing, the resource schema also determines: 
+ What unit test stubs are generated in your resource package, and what contract tests are appropriate to run for the resource\. When you run the CloudFormation CLI ` generate` command, the CloudFormation CLI generates empty unit tests based on the properties of the resource and their attributes\.
+ Which contract tests are appropriate for CloudFormation CLI to run for your resources\. When you run the ` test` command, the CloudFormation CLI runs the appropriate contract tests, based on which handlers are included in your resource schema\.

## Defining property attributes<a name="resource-type-model-setting-properties"></a>

Certain properties of a resource may have special meaning when used in different contexts\. For example, a given resource property may be read\-only when read back for state changes, but can be specified when used as the target of a $ref from a related resource\. Because of this semantic difference in how this property metadata should be interpreted, certain property attributes are defined at the resource level, rather than at a property level\.

These attributes include:
+ `primaryIdentifier`
+ `additionalIdentifiers`
+ `createOnlyProperties`
+ `readOnlyProperties`
+ `writeOnlyProperties`

For reference information on resource schema elements, see [Resource type schema](resource-type-schema.md)\.

## How to define a minimal resource<a name="resource-type-howto-minimal"></a>

The example below displays a minimal resource type definition\. In this case, the resource consists of a single optional property, `Name`, which is also specified as its primary \(and only\) identifier\.

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

## Defining the account\-level configuration of an extension<a name="resource-type-howto-configuration"></a>

There might be cases where your extension includes properties that the user must specify for all instances of the extension in a given account and Region\. In such cases, you can define those properties in a *configuration definition* that the user then sets at the Region level\. For example, if your extension needs to access a third\-party web service, you can include a configuration for the user to specify their credentials for that service\.

When the user sets the configuration, CloudFormation validates it against the configuration definition, and then saves this information at the Region level\. From then on, CloudFormation can access that configuration during operations involving any instances of that extension in the Region\. Configurations are available to CloudFormation during all resource operations, including `read` and `list` events that don't explicitly involve a stack template\.

**Note**  
Configuration definitions are not compatible with [module](modules.md) extensions\.

Your configuration definition must validate against the [provider configuration definition meta\-schema](https://github.com/aws-cloudformation/cloudformation-cli/blob/master/src/rpdk/core/data/schema/provider.configuration.definition.schema.v1.json)\.

The `CloudFormation` property name is reserved, and cannot be used to define any properties in your configuration definition\.

Use the `typeConfiguration` element of the [provider definition meta\-schema](https://github.com/aws-cloudformation/cloudformation-cli/blob/master/src/rpdk/core/data/schema/provider.definition.schema.v1.json) to include the configuration definition as part of your extension's schema\.

**Important**  
It is strongly recommended that you use dynamic references to restrict sensitive configuration definitions, such as third\-party credentials, as in the example below\. For more details on dynamic references, see [Using dynamic references to specify template values](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html) in the *AWS CloudFormation User Guide*\.

### Example: Defining a configuration definition to specify third\-party credentials<a name="resource-type-howto-configuration-example"></a>

The following example illustrates how you might model third\-party credentials in an extension\. The schema below for the `MyOrg::MyService::Resource` resource type includes a `typeConfiguration` section\. The configuration definition includes a required property, `ServiceCredentials`, of type `Credentials`\. As defined in the `definitions` section, the `Credentials` type includes two properties for the user to specify their credentials for a third\-party service: `ApiKey` and `ApplicationKey`\.

In this example, both properties must be dynamic references, as represented by the regex pattern for each property\. By using dynamic references here,CloudFormation never stores the actual credential values, but instead retrieves them from AWS Secrets Manager or Systems Manager Parameter Store only when necessary\. For more information about dynamic references, including how CloudFormation distinguishes which service to retrieve values from, see [Using dynamic references to specify template values](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html) in the *AWS CloudFormation User Guide*\.

To see how users set configuration data for their extensions, see [Configuring extensions at the account level](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/registry-register.html#registry-set-configuration) in the *AWS CloudFormation User Guide*\.

```
{
    "typeName": "MyOrg::MyService::Resource",
    "description": "Example resource type that requires third-party credentials",
    "additionalProperties": false,
    "typeConfiguration": {
        "properties": {
            "ServiceCredentials": {
                "$ref": "#/definitions/Credentials"
            }
        },
        "additionalProperties": false,
        "required": [
            "ServiceCredentials"
        ]
    },
    "definitions": {
        "Credentials": {
            "type": "object",
            "properties": {
                "ApiKey": {
                    "description": "Third-party API key",
                    "type": "string",
                    "pattern": "{{resolve:.*:[a-zA-Z0-9_.-/]+}}"
                },
                "ApplicationKey": {
                    "description": "Third-party application key",
                    "type": "string",
                    "pattern": "{{resolve:.*:[a-zA-Z0-9_.-/]+}}"
                }
            },
            "additionalProperties": false
        }
    },
    "properties": {
        "Id": {
            "type": "string"
        },
        "Name": {
            "type": "string"
        }
    },
    "primaryIdentifier": [
        "/properties/Id"
    ],
    "additionalIdentifiers": [
        ["/properties/Name"]
    ],
    "handlers": {

    }
}
```