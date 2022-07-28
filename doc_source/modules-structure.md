# Module structure<a name="modules-structure"></a>

A module consists of two main pieces:
+ A *template fragment*, which defines the resources and associated information you want to provision through use of the module, including any module parameters you define\.
+ A *module schema* that you generate based on the template fragment\. The module schema declares the contract you defined in the template fragment, and is viewable to users in the CloudFormation registry\.

## Creating the module template fragment<a name="modules-template-fragment"></a>

The starting point for developing a module is the template fragment\. The template fragment is a file that contains the information that defines the resources for CloudFormation to provision during stack operations, including:
+ A `[Resources](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resources-section-structure.html)` section that defines the resources to be provisioned\.

  The `Resources` section is required\.
+ Additional other template sections related for the provisioning of the resources as necessary, such as [Outputs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html) and [Conditions](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/conditions-section-structure.html)\.
+ A `Parameters` section for any optional module\-level parameters you want to define\.

  Much like [template parameters](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html), module parameters enable the user to input custom values to a module from the template \(or module\) that contains it\. The module can then use these values to set properties of the resources it contains\.

Currently, CloudFormation supports template fragments written in JSON or YAML\.

For example, the following template fragment creates an S3 bucket resource, and sets the `AccessControl` property to `Private` and the resource `DeletionPolicy` to `Retain`\. In addition, the template fragment defines a module\-level parameter, `VersioningConfigurationParam`, whose values is used to set the `VersioningConfiguration` status of the S3 bucket\.

```
{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "A sample S3 Bucket module (AWS::SampleS3::Bucket::MODULE)",
    "Parameters": {
        "VersioningConfigurationParam": {
            "Description": "Versioning configuration",
            "Type": "String"
        }
    },
    "Resources": {
        "S3BucketName": {
            "Type": "AWS::S3::Bucket",
            "Properties": {
                "AccessControl": "Private",
                "VersioningConfiguration": {
                    "Status": {
                        "Ref": "VersioningConfigurationParam"
                    }
                }
            },
            "DeletionPolicy": "Retain"
        }
    }
}
```

You can author template fragments manually, or use any tool that generates CloudFormation templates\. For example, you can use the AWS Cloud Development Kit \(CDK\) to synthesize one or more CDK [constructs](https://docs.aws.amazon.com/cdk/latest/guide/constructs.html) to produce a CloudFormation template, and then use that template as the basis for a module\. For more information on the CDK, see the *[AWS Cloud Development Kit \(CDK\)](https://docs.aws.amazon.com/cdk/latest/guide/home.html)*\.

**Note**
Be aware that regardless of the method you use to create a module's template fragment, it must adhere to the restrictions on what can be included in a template fragment for a module\.

### Considerations when authoring the template fragment<a name="modules-considerations"></a>

Keep in mind the following considerations when developing modules:
+ Modules are, by design, predictable, and transparent\. Because of this, you cannot include features which can potentially result in external information or resources being imported into the module\. These features include:
  + [Importing](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-imports.html) stack values, using [Fn::ImportValue](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-importvalue.html) intrinsic function\.
  + [Exporting](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-exports.html) stack values, using the `Export` field in the [Outputs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html) template section\. \(Use of the `Outputs` section is supported\.\)
  + [Macros](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-macros.html), including use of the [Transform](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/transform-reference.html) template section or the [Fn::Transform](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-transform.html) function\.

    This includes transforms provided by CloudFormation, such as [AWS::Include](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/create-reusable-transform-function-snippets-and-add-to-your-template-with-aws-include-transform.html) and [AWS::Serverless](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/transform-aws-serverless.html)\.
  + [Nested stacks](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-nested-stacks.html), which are represented in the template by the [AWS::CloudFormation::Stack](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-stack.html) resource\.
  + Stack sets, which are represented in the template by the [AWS::CloudFormation::StackSet](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-cloudformation-stackset.html) resource\.
+ Tags can't be specified at the module level\. However:
  + You can assign tags to individual resources within the module, as you would assign tags to any resource\.
  + You can use module parameters to set tag values\.

    Create the module parameter, and then have the tag you've assigned to individual resources within the module reference that module parameter\. For more information, see [Using parameters to specify module values](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/module-using-params.html) in the *CloudFormation User Guide*\.
  + Tags you specify at the *stack* level are assigned to the individual resources derived from the module\.
+ Helper scripts specified at the module level do not propagate to the individual resources contained in the module when CloudFormation processes the template\.
+ Outputs specified in the module are propagated to outputs at the template level\.

  Each output will be assigned a logical ID that's a concatenation of the module logical name and the output name as defined in the module\. For more information on outputs, see [Outputs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html) in the *CloudFormation User Guide*\.
+ Parameters specified in the module Aren't propagated to parameters at the template level\.

  However, you can create template\-level parameters that reference module\-level parameters\. For more information, see [Using parameters to specify module values](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/modules.html#module-using-params) in the *CloudFormation User Guide*\.

### Nesting modules<a name="modules-nesting"></a>

Modules can contain other modules\. You can nest modules up to three levels deep\. To include a module in your module, reference it in the `Resources` section of your template fragment, as you would any other resource\. For an example, see [Specifying properties on resources in a child module from the parent module](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/modules.html#module-using-params-example-2) in the *CloudFormation User Guide*\.

### Macros and modules<a name="modules-macros"></a>

CloudFormation doesn't support inclusion of modules in macros\. A module can't contain a macro\.

For more information on macros, see [Using macros to perform custom processing](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-macros.html) in the *CloudFormation User Guide*\.

### Defining parameters in a module<a name="modules-parameters"></a>

Much like template parameters, module parameters enable the user to input custom values to a module from the template \(or module\) that contains it\. The module can then use these values to set properties of the resources it contains\.

You define a module parameter as you would a template parameter\. For detailed information about parameter requirements and definition, see [Parameters](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html) in the *CloudFormation User Guide*\.

[Dynamic references](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html) aren't resolved when the module is processed by CloudFormation, but when the individual resources are created or updated during stack operations\.

Module parameters don't count toward the parameter maximum for template parameters\. For information on template parameters and their limits, see [Parameters](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html) in the *CloudFormation User Guide*\.

Parameters specified in the module are not propagated to parameters at the template level\. However, you can create template\-level parameters that reference module\-level parameters\.

For information on how users can specify parameter values in modules, see [Using parameters to specify module values](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/modules.html#module-using-params) in the *CloudFormation User Guide*\.

#### Specifying constraints for module parameters<a name="modules-parameters-constraints"></a>

Module parameters don't support [Constraint](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html#parameters-section-structure-properties) enforcement\. To perform constraint checking on a module parameter, create a template parameter with the desired constraints, then reference that template parameter in your module parameter\.

### Specifying policies on resources contained in a module<a name="modules-policies"></a>

If you specify the following resource policy attributes at the module level, CloudFormation applies the policy attribute to *all* resources contained in the module:
+ `DeletionPolicy`
+ `UpdateReplacePolicy`

  This doesn't include specifying the `Snapshot` option for `UpdateReplacePolicy`\. Specify this option on the resource directly\.

Policy attributes specified at a resource level override any specified at the module level\.

You can't specify the following resource policy attributes at the module level:
+ `CreationPolicy`
+ `UpdatePolicy`

If you use a `DependsOn` attribute to specify that a resource in your template depends on a module, CloudFormation will finish provisioning *all* resources in the module before provisioning the dependent resource\.

For more information on resource policies, see [Resource attribute reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-product-attribute-reference.html) in the *CloudFormation User Guide*\.

## Generating the module schema<a name="modules-schema"></a>

The module schema is generated from the template fragment, and defines the contract to which the module adheres, including defining the input it accepts and the possible resources it resolves to when included in a template\.

To generate the module schema, use the `[validate](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-cli-validate.html)` command once you've authored your template fragment\.

For example, suppose you created a module package and used the template fragment above\. The `validate` command would result in the following module schema:

```
{
  "typeName": "AWS::SampleS3::Bucket::MODULE",
  "properties": {
    "VersioningConfigurationParam": {
      "description": "Version Configuration",
      "type": "string"
    }
  },
  "resources": {
    "type": "object",
    "properties": {
      "S3Bucket": {
        "$ref": "aws-s3-bucket.json"
      }
    },
    "additionalProperties": false
  }
}
```

For more information, see [Develop a module](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/modules-develop.html)\.

## Model requirements for publishing a public module<a name="modules-structure-publishing-prereqs"></a>

If you want to make your module publicly available to all CloudFormation users, you can publish it to the CloudFormation registry\. In order to publish your module, it must meet the following model requirements\. Prior to publishing, use [TestType](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_TestType.html) to confirm your module meets these requirements\.

For more information on publishing public extensions, see [Publishing extensions to make them available for public use](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/publish-extension.html#publish-extension-publishing)\.
+ Public modules can contain other public modules as child modules, to a level of three deep\.
+ Public modules cannot include circular dependencies on child modules, or vice versa\.
+ [Custom resources](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources.html) are not supported in public modules\.
+ Only public resources are supported in public modules\. The public resources can be published by Amazon or third\-parties\.
+ Any third\-party public resources included in the module must include the necessary publisher information, as detailed in [Specifying publisher metadata for public third\-party resources](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/modules-structure.html#modules-structure-publishing-3p-info)\.
+ The supported major versions listed in the module for a resource type must be subset of the supported major versions specified for the resource type in any child modules\.

### Specifying publisher metadata for public third\-party resources<a name="modules-structure-publishing-3p-info"></a>

For any third\-party public resources you include in your public module, you must specify additional publisher information\. This enables CloudFormation to determine the resource type specified, and which versions of that resource the module supports\. Specify the following properties in a [Metadata](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/metadata-section-structure.html) element in your resource definition:
+ `PublisherId`

  The publisher ID of the resource type publisher\.
+ `RegionalPublisherId`

  An array listing the regions in which the publisher is registered, with the publisher ID in each region\.
+ `OrignalTypeName`

  The original type name of the resource type, as specified by the publisher\.
+ `SupportMajorVersions`

  An array listing the major versions of the resource this module supports\.

For example, the following module snippet adds a resource to the module\. The module uses a type alias, `Module::DDB::Table`, for the resource type, but also includes the original type name, `Mongodb::DDB::Table`, so that CloudFormation can determine if the resource type is enabled in the user's account\. The snippet also includes publisher ID information, in case multiple publishers have published public resource types of the same name, as well as which major versions of the resource type that the module supports\.

```
Resources:
  SampleDDB:
    Type: Module::DDB::Table
    Properties:
       TableName: xx
       IndexName: xxx
    Metadata:
      PublisherId: dfdxfdfwed
      RegionalPublisherId:
        us-east-1: c34ntbnrb1
        us-west-2: eer332gfdf
      OrignalTypeName:
         Mongodb::DDB::Table
      SupportMajorVersions: [1, 2, 3]
    .....
```
