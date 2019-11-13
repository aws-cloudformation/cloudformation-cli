# Creating Resource Providers<a name="resource-types"></a>

If you use third\-party resources in your infrastructure and applications, you can now model and automate those resources by developing them as* resource providers* for use within CloudFormation\. A resource provider includes a resource type specification, and handlers that control API interactions with the underlying AWS or third\-party services\. These interactions include create, read, update, delete and list \(CRUDL\) operations for resources\. Use resource providers to model and provision resources using CloudFormation\.

Resource providers are treated as first\-class citizens within CloudFormation; you can use CloudFormation capabilities to create, provision, and manage these custom resources in a safe and repeatable manner, just as you would any AWS resource\. Using resource providers for third\-party resources provides you a way to reliably manage these resources using a single tool, without having to resort to time\-consuming and error\-prone methods like manual configuration or custom scripts\.

You can create resource providers and make them available for use within the AWS account in which they are registered\.

## Using the CloudFormation CLI to Create Resource Providers<a name="resource-types-rpdk"></a>

Use the [AWS CloudFormation Command Line Interface \(CLI\)](https://github.com/aws-cloudformation/aws-cloudformation-rpdk) to develop your resource providers\. The CloudFormation CLI is an open\-source project that provides a consistent way to model and provision both AWS and third\-party resources using CloudFormation\. It includes commands to enable each step of creating your resource providers\.

There are three major steps in developing a resource providers:
+ Model

  Create and validate a schema that serves as the canonical definition of your resource provider\.

  Use the `[init](resource-type-cli-init.md)` command to generate your resource project, including an example resource schema\. Edit the example schema to define the actual model of your resource provider\. This includes resource properties and their attributes, as well specifying resource event handlers and any permissions needed for each\.

  As you iterate on your resource model, you can use the `[validate](resource-type-cli-validate.md)` command to validate your schema against the [Resource Provider Definition Schema](https://github.com/aws-cloudformation/aws-cloudformation-rpdk/blob/master/src/rpdk/core/data/schema/provider.definition.schema.v1.json) and fix any issues\.
+ Develop

  Add logic that controls what happens to the resource at each stage in its lifecycle, and then test the resource locally to ensure it works as expected\.

  Implement the resource provisioning actions that the CloudFormation CLI stubbed out when you initially generated your resource project\.

  If you make changes to your resource schema, use the `[generate](resource-type-cli-generate.md)` command to generate the language\-specific data model, contract test, and unit test stubs based on the current state of the resource schema\. \(If you use the Java add\-in for the CloudFormation CLI, this is done for you automatically\.\)

  When you're ready to test the resource behavior, the CloudFormation CLI provides two commands for testing:
  + Use the `invoke` command to test a single handler\.
  + Use the `[test](resource-type-cli-test.md)` command to run the entire suite of resource contract tests locally, using the AWS SAM Command Line Interface \(SAM CLI\), to make sure the handlers you've written comply with expected handler behavior at each stage of the resource lifecycle\.
+ Register

  Register the resource provider with the CloudFormation registry in order to make it available for use in CloudFormation templates\.

  Use the `[submit](resource-type-cli-submit.md)` command to register the resource provider with CloudFormation and make it available for use in CloudFormation operations\. Registration includes:
  + Validating the resource schema\.
  + Packaging up the resource project files and uploading them to CloudFormation\.
  + Registering the resource definition in your account, in the specified region\.

  You can register multiple versions of a resource provider, and specify which version you want users to use by default\.
