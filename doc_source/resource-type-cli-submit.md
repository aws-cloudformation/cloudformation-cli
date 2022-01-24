# submit<a name="resource-type-cli-submit"></a>

## Description<a name="resource-type-cli-submit-description"></a>

Registers the extension with CloudFormation, in the specified region\. Registering a extension makes it available for use in CloudFormation operations\.

Registering includes:
+ Validating the resource schema\.
+ Packaging up the resource project files and uploading them to CloudFormation\.

  This includes the source code for your resource handlers\. These resource handlers run within the CloudFormation account\.
+ Determining which handlers have been specified for the resource, and running the appropriate contract tests\.
+ Uploading the resource handlers as functions that CloudFormation calls at the appropriate times in a resource's lifecycle\.
+ Returning a *registration token* that you can use with the [DescribeTypeRegistration](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeTypeRegistration.html) action to track the status of the registration request\.

**Note**
The user registering the extension must be able to access the schema handler package in the S3 bucket\. That is, the user needs to have [GetObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html) permissions for the schema handler package\. For more information, see [Actions, Resources, and Condition Keys for Amazon S3](https://docs.aws.amazon.com/IAM/latest/UserGuide/list_amazons3.html) in the *AWS Identity and Access Management User Guide*\.

## Synopsis<a name="resource-type-cli-submit-synopsis"></a>

```
  cfn submit
[--dry-run]
[--endpoint-url <value>]
[--region <value>]
[--role-arn <value>]
[--no-role]
[--set-default]
```

## Options<a name="resource-type-cli-submit-options"></a>

`--dry-run`

Validate the schema and package up the project files, but don't register the extension with CloudFormation\.

`--endpoint-url <value>`

The CloudFormation endpoint to use\.

`--region <value>`

The AWS Region in which to register the extension\. If no Region is specified, the extension is registered in the default region\.

`--role-arn <value>`

A specific IAM role to use when invoking handler operations\.

If you don't specify an IAM role, the CloudFormation CLI attempts to create or update an execution role based on the execution role template derived from the resource type's schema, and then passes this execution role to CloudFormation\. For more information, see [Accessing AWS APIs from a Resource Type](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-develop.html#resource-type-develop-executionrole)\.

You can't specify both `--role-arn` and `--no-role` arguments\.

`--no-role`

Prevent the CloudFormation CLI from passing an execution role to CloudFormation\.

If your resource type calls AWS APIs in any of its handlers, you must either specify a role arn, or have the CloudFormation CLI create or update an execution role and pass that execution role to CloudFormation\. For more information, see [Accessing AWS APIs from a Resource Type](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-develop.html#resource-type-develop-executionrole)\.

You can't specify both `--role-arn` and `--no-role` arguments\.

`--set-default`

Upon successful registration of the type version, sets the current type version as the default version\.

## Output<a name="resource-type-cli-submit-output"></a>

Extension registration is an asynchronous operation\. You can use the supplied registration token to track the progress of your extension registration request using the [DescribeTypeRegistration](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeTypeRegistration.html) action of the CloudFormation API\.
