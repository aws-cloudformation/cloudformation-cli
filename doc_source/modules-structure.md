# Module structure<a name="modules-structure"></a>

A module consists of two main peices:
+ A *template fragment*, which defines the resources and associated information you want to provision through use of the module, including any module parameters you define\.
+ A *module schema* that you generate based on the template fragment\. The module schema declares the contract you defined in the template fragment, and is viewable to users in the CloudFormation registry\.

## Creating the module template fragment<a name="modules-template-fragment"></a>

The starting point for developing a module is the template fragment\. The template fragment is a file that contains the information that defines the resources for CloudFormation to provision during stack operations, including:
+ A `[Resources](https://docs.aws.amazon.com/)` section that defines the resources to be provisioned\.

  The `Resources` section is required\.
+ Additional other template sections related for the provisioning of the resources as necessary, such as [Outputs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html) and [Conditions](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/conditions-section-structure.html)\.
+ A `Parameters` section for any optional module\-level parameters you want to define\.

  Much like [template parameters](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html), module parameters enable the user to input custom values to a module from the template \(or module\) that contains it\. The module can then use these values to set properties of the resources it contains\. 

Currently, CloudFormation supports template fragments written in JSON\.

For example, the following template fragment creates an S3 bucket resource, and sets the `AccessControl` property to `Private` and the resource `DeletionPolicy` to `Retain`\. In addition, the template fragment defines a module\-level parameter, `VersioningConfigurationParam`, whose values is used to set the `VersioningConfiguration` status of the S3 bucket\.

```
{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "A sample S3 Bucket module (AWS::SampleS3::Bucket::MODULE)'",
    "Parameters": {
        "VersioningConfigurationParam": {
            "Description": "Versioning configuration",
            "Type": "String",
            "AllowedValues": [
                "Enabled",
                "Suspended"
            ]
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

You can author template fragments manually, or use any tool that generates CloudFormation templates\. For example, you can use the AWS Cloud Development Kit \(AWS CDK\) to synthesize one or more CDK [constructs](https://docs.aws.amazon.com/cdk/latest/guide/constructs.html) to produce a CloudFormation template, and then use that template as the basis for a module\. For more information on the CDK, see the *[AWS Cloud Development Kit](https://docs.aws.amazon.com/cdk/latest/guide/home.html)*\.

**Note**  
Be aware that regardless of the method you use to create a module's template fragment, it must adhere to the restrictions on what can be included in a template fragment for a module\.

### Considerations when authoring the template fragment<a name="modules-considerations"></a>

Keep in mind the following considerations when developing modules:
+ Modules are, by design, predictable and transparent\. Because of this, you cannot include features which can potentially result in external information or resources being imported into the module\. These features include: 
  + [Importing](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-imports.html) stack values, using [Fn::ImportValue](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-importvalue.html) intrinsic function\.
  + [Exporting](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-exports.html) stack values, using the `Export` field in the [Outputs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html) template section\. \(Use of the `Outputs` section is supported\.\)
  + [Macros](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-macros.html), including use of the [Transform](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/transform-reference.html) template section or the [Fn::Transform](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-transform.html) function\.

    This includes transforms provided by CloudFormation, such as [AWS::Include](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/create-reusable-transform-function-snippets-and-add-to-your-template-with-aws-include-transform.html) and [AWS::Serverless](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/transform-aws-serverless.html)\.
  + [Nested stacks](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-nested-stacks.html), which are represented in the template by the [AWS::CloudFormation::Stack](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-stack.html) resource\.
  + Stack sets, which are represented in the template by the [AWS::CloudFormation::StackSet](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-cloudformation-stackset.html) resource\.
+ Tags cannot be specified at the module level\. However:
  + You can assign tags to individual resources within the module, as you would assign tags to any resource\.
  + You can use module parameters to set tag values\. 

    Create the module parameter, and then have the tag you've assigned to individual resources within the module reference that module parameter\. For more information, see [Using parameters to specify module values](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/module-using-params.html) in the *CloudFormation User Guide*\.
  + Tags you specify at the *stack* level are assigned to the individual resources derived from the module\.
+ Helper scripts specified at the module level do not propagate to the individual resources contained in the module when CloudFormation processes the template\.
+ Outputs specified in the module are propagated to outputs at the template level\.

  Each output will be assigned a logical ID that is a concatenation of the module logical name and the output name as defined in the module\. For more information on outputs, see [Outputs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html) in the *CloudFormation User Guide*\.
+ Parameters specified in the module are not propagated to parameters at the template level\.

  However, you can create template\-level parameters that reference module\-level parameters\. For more information, see [Using parameters to specify module values](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/module-using-params.html) in the *CloudFormation User Guide*\.

### Nesting modules<a name="modules-nesting"></a>

Modules can contain other modules\. You can nest modules up to three levels deep\. To include a module in your module, reference it in the `Resources` section of your template fragment, as you would any other resource\. For an example, see [Specifying properties on resources in a child module from the parent module](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/module-using-params-example-2) in the *CloudFormation User Guide*\.

### Macros and modules<a name="modules-macros"></a>

CloudFormation does not support inclusion of modules in macros\. A module cannot contain a macro\.

For more information on macros, see [Using macros to perform custom processing](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-macros.html) in the *CloudFormation User Guide*\.

### Defining parameters in a module<a name="modules-parameters"></a>

Much like template parameters, module parameters enable the user to input custom values to a module from the template \(or module\) that contains it\. The module can then use these values to set properties of the resources it contains\. 

You define a module parameter as you would a template parameter\. For detailed information about parameter requirements and definition, see [Parameters](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html) in the *CloudFormation User Guide*\.

[Dynamic references](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html) are not resolved when the module is processed by CloudFormation, but when the individual resources are created or updated during stack operations\.

Module parameters do not count toward the parameter maximum for template parameters\. For information on template parameters and their limits, see [Parameters](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html) in the *CloudFormation User Guide*\.

Parameters specified in the module are not propagated to parameters at the template level\. However, you can create template\-level parameters that reference module\-level parameters\.

For information on how users can specify parameter values in modules, see [Using parameters to specify module values](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/modules.html#module-using-params) in the *CloudFormation User Guide*\.

#### Specifying constraints for module parameters<a name="modules-parameters-constraints"></a>

Module parameters do not support [Type or Constraint](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html#parameters-section-structure-properties) enforcement\. To perform type or constraint checking on a module parameter, create a template parameter with the desired constraints, then reference that template parameter in your module parameter\.

### Specifying policies on resources contained in a module<a name="modules-policies"></a>

If you specify the following resource policy attributes at the module level, CloudFormation applies the policy attribute to *all* resources contained in the module:
+ `DeletionPolicy`
+ `UpdateReplacePolicy`

  This does not include specifying the `Snapshot` option for `UpdateReplacePolicy`\. Specify this option on the resource directly\.

Policy attributes specified at a resource level override any specified at the module level\.

You cannot specify the following resource policy attributes at the module level:
+ `CreationPolicy`
+ `UpdatePolicy`

If you use a `DependsOn` attribute to specify that a resource in your template depends on a module, CloudFormation will finish provisioning *all* resources in the module before provisioning the dependant resource\.

For more information on resource policies, see [Resource attribute reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-product-attribute-reference.html) in the *ClooudFormation User Guide*\.

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
