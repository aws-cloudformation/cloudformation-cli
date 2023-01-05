# Creating resource types<a name="resource-types"></a>

If you use third\-party resources in your infrastructure and applications, you can now model and automate those resources by developing them as* resource types* for use within CloudFormation\. A resource type includes a resource type specification and handlers that control API interactions with the underlying AWS or third\-party services\. These interactions include create, read, update, delete, and list \(CRUDL\) operations for resources\. Use resource types to model and provision resources using CloudFormation\.

Resource types are treated as first\-class citizens within AWS CloudFormation you can use AWS CloudFormation capabilities to create, provision, and manage these custom resources in a safe and repeatable manner, just as you would any AWS resource\. Using resource types for third\-party resources provides you a way to reliably manage these resources using a single tool, without having to resort to time\-consuming and error\-prone methods like manual configuration or custom scripts\.

You can create resource types and make them available for use within the AWS account in which they are registered\.

## Using the CloudFormation CLI to create resource types<a name="resource-types-rpdk"></a>

Use the [CloudFormation Command Line Interface \(CLI\)](https://github.com/aws-cloudformation/aws-cloudformation-rpdk) to develop your resource types\. The CloudFormation CLI is an open\-source project that provides a consistent way to model and provision both AWS and third\-party resources using CloudFormation\. It includes commands to enable each step of creating your resource types\.

There are three major steps in developing a resource types:
+ Model

  Create and validate a schema that serves as the canonical definition of your resource type\.

  Use the `init` command to generate your resource project, including an example resource schema\. Edit the example schema to define the actual model of your resource type\. This includes resource properties and their attributes, as well specifying resource event handlers and any permissions needed for each\.

  As you iterate on your resource model, you can use the `validate` command to validate your schema against the [Resource type definition schema](https://github.com/aws-cloudformation/aws-cloudformation-rpdk/blob/master/src/rpdk/core/data/schema/provider.definition.schema.v1.json) and fix any issues\.
+ Develop

  Add logic that controls what happens to the resource at each stage in its lifecycle, and then test the resource locally to ensure it works as expected\.

  Implement the resource provisioning actions that the CloudFormation CLI stubbed out when you initially generated your resource project\.

  If you make changes to your resource schema, use the `generate` command to generate the language\-specific data model, contract test, and unit test stubs based on the current state of the resource schema\. \(If you use the Java add\-in for the CloudFormation CLI, this is done for you automatically\.\)

  When you're ready to test the resource behavior, the CloudFormation CLI provides two commands for testing:
  + Use the `invoke` command to test a single handler\.
  + Use the `test` command to run the entire suite of resource contract tests locally, using the AWS SAM Command Line Interface \(SAM CLI\), to make sure the handlers you've written comply with expected handler behavior at each stage of the resource lifecycle\.
+ Register

  Register the resource type with the CloudFormation registry in order to make it available for use in CloudFormation templates\.

  Use the `submit` command to register the resource type with CloudFormation and make it available for use in CloudFormation operations\. Registration includes:
  + Validating the resource schema\.
  + Packaging up the resource project files and uploading them to CloudFormation\.
  + Registering the resource definition in your account, in the specified Region\.

  You can register multiple versions of a resource type, and specify which version you want users to use by default\.
