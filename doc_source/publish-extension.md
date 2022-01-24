# Publishing extensions to make them available for public use<a name="publish-extension"></a>

After you've developed and registered a private extension, you can make it publicly available to general CloudFormation users by *publishing* it to the CloudFormation registry, as a third\-party public extension\.

Public third\-party extensions enable you to offer CloudFormation users ways to model, provision, and configure environments containing AWS and third\-party resources\. As with private extensions, public extensions are treated the same as any resource published by Amazon within CloudFormation; users can use CloudFormation capabilities to create, provision, and manage the extensions you provide in a safe and repeatable manner, just as they would any AWS resource\. This includes CloudFormation management capabilities such as change sets, drift detection, and resource import\.

Extensions published to the registry are visible by all CloudFormation users in the Regions in which they're published\. Users can then *activate* your extension in their account, which makes it available for use in their templates\. For more information, see [Using public extensions in CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/registry-public.html) in the *CloudFormation User Guide*\.

**Note**
If your public extension implements event handlers, users of the extension may incur charges to their account\. For example, suppose your public extension is a resource type with create, read, update, list, and delete handlers\. Users using your extension in their stacks would incur charges when your handler code executes during the various resource create, read, update, list, and delete stack operations\. This is in addition to any charges incurred for the resources themselves running\.
For more information, see [AWS CloudFormation pricing](https://aws.amazon.com/cloudformation/pricing/)\.

## Developing a public extension for CloudFormation<a name="publish-extension-overview"></a>

To develop a public third\-party extension, develop your extension as a private extension\. Then, in each Region in which you want to make the extension publicly available:

1. [Register your extension](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-register.html) as a private extension in the CloudFormation registry\.

1. [Test your extension](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/publish-extension.html#publish-extension-testing) to make sure it meets all necessary requirements for being published in the CloudFormation registry\.

1. [Publish your extension](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/publish-extension.html#publish-extension-publishing) to the CloudFormation registry\.
**Note**
Before you publish any extension in a given Region, you must first register as an extension publisher in that Region\.

   To do this in multiple Regions simultaneously, see [Publishing your extension in multiple Regions using StackSets](publish-extension-stacksets.md)\.

## Pre\-requisite: Registering your account to publish CloudFormation extensions<a name="publish-extension-prereqs"></a>

To publish third\-party extensions, register your extension publisher with CloudFormation\. To do so, you must have an account with one of the following services\. CloudFormation uses these services to verify your public identity as a publisher:
+ [AWS Marketplace](https://aws.amazon.com/marketplace/management/tour?ref_=header_modules_sell_in_aws)
+ [Bitbucket](https://bitbucket.org/)
+ [GitHub](https://github.com/)
**Note**
CloudFormation doesn't currently support GitHub Enterprise Cloud or GitHub Enterprise Server accounts for identity verification\.

If you use your Bitbucket or GitHub account, you must create a connection between that account and the AWS account which you want to register as a publisher\. For more information, see the following topics in the *Developer Tools Console User Guide*:
+ [Create a connection to Bitbucket](https://docs.aws.amazon.com/dtconsole/latest/userguide/connections-create-bitbucket.html)
+ [Create a connection to GitHub](https://docs.aws.amazon.com/dtconsole/latest/userguide/connections-create-github.html)

Use [RegisterPublisher](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_RegisterPublisher.html) to register your account to publish extensions\. As part of registering as a publisher, you must accept the **[Terms and Conditions](https://cloudformation-registry-documents.s3.amazonaws.com/Terms_and_Conditions_for_AWS_CloudFormation_Registry_Publishers.pdf)** for extension publishers\. If you use a Bitbucket or GitHub account for identity verification, you'll need to supply CloudFormation the Amazon Resource Name \(ARN\) for your connection to that account\.

In addition, you'll need the following permissions:
+ `codestar-connections:GetConnection`
+ `codestar-connections:UseConnection`

For more information, see [AWS CodeStar Connections permissions reference](https://docs.aws.amazon.com/dtconsole/latest/userguide/security-iam.html#permissions-reference-connections) in the *Developer Tools console User Guide*\.

When you register, CloudFormation assigns your account a publisher ID under which your extensions will be published\. This publisher ID applies across all AWS Regions\.

## Testing your public extension prior to publishing<a name="publish-extension-testing"></a>

In order to publish your public extension, it must pass all test requirements defined for it:
+ For resource types, this includes passing all contracts tests defined for the type\. For more information on testing resource types, see [Testing resource types using contract tests](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test.html)\.
+ For modules, this includes determining if the module's model meets all necessary requirements\. For information on publication requirements for modules, see [Requirements for publishing a public module](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/modules-structure.html#modules-structure-publishing-prereqs)\.

Use [TestType](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_TestType.html) to have CloudFormation perform the required tests on an extension\. After running the test, CloudFormation assigns a test status to the extension\. An extension must have a test status of `PASSED` in a given Region before it can be published there\.

If you don't specify a version, CloudFormation uses the default version of the extension in your account and Region for testing\.

Because testing may take some time, `TestType` is an asynchronous operation\. Once you've initiated testing on an extension using `TestType`, you can use [DescribeType](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeType.html) to monitor the current test status and test status description for the extension\.

The tests that CloudFormation runs against your extension are non\-exhaustive and generic, which means that you should also thoroughly test your extension to ensure that it performs as expected\. Using your privately registered extension in stack templates is the CloudFormation equivalent of testing your extension in a sandbox environment\. Publishing your extension does not change any provisioning behavior of your extension; it only makes it available to all customers in the Region in which the extension is published\.

## Publishing your public extension to the CloudFormation registry<a name="publish-extension-publishing"></a>

After your extension has passed all necessary test requirements, you can publish it to make it publicly available for use through the CloudFormation registry\. Publishing your extension makes it available in all AWS accounts in the Region\. Use `[PublishType](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_PublishType.html)` to publish your extension in each desired Region\.

### Versioning your public extension<a name="publish-extension-version"></a>

When publishing your extension, you can specify a public version number\. This is separate and distinct from the private extension version that CloudFormation assigns to a private extension when you register it\. If you don't specify a version number, CloudFormation increments the version number by one minor version release\.

Use the following format, and adhere to semantic versioning when assigning a version number to your extension:

`MAJOR.MINOR.PATCH`

For more information, see [Semantic Versioning 2\.0\.0](https://semver.org/)\.

#### Versioning and updating activated public extensions<a name="publish-extension-version-auto"></a>

When a user activates a public extension for use in their account, they have the option to have CloudFormation automatically update to using a new minor version whenever one is released by the extension publisher\. This only applies to *minor* version changes, including patches\. For major version changes, users are required to manually update to a new major version of an extension\.

Increment to a new major version if the new version possibly contains breaking changes\.

### Open\-sourcing your public extension project<a name="publish-extension-opensource"></a>

It's considered a best practice to open\-source your public extensions\.
