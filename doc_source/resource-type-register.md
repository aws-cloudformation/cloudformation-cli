# Registering extensions for use in the CloudFormation registry<a name="resource-type-register"></a>

Once you've completed developing your extension, you'll need to *register* it with CloudFormation in order to make it available for use in the CloudFormation registry\. From the CloudFormation CLI, use the `submit` command to register your extension with CloudFormation\. You can also register your resource directly using the [RegisterType](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_RegisterType.html) action\.

For detailed information on registering private extensions, see [Using private extensions](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/registry-register.html) in the *AWS CloudFormation User Guide*\.

## Registering extensions using the `submit` command<a name="resource-type-register-submit"></a>

In general, the `submit` command does the following:
+ Validates the extension schema\.
+ Packages up the extension project files and uploads them to CloudFormation\.

  This includes any source code, such as resource handlers for resource type extensions\. Extension source code, such as resource handlers runs within the CloudFormation service account\.
+ Runs the unit and contract tests defined in the extension project\.
+ For resource type extensions, determines which handlers have been specified for the resource, to determine how CloudFormation provisions the resource\.
+ Returns a *registration token* that you can use with the [DescribeTypeRegistration](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeTypeRegistration.html) action to track the status of the registration request\.

To validate and package your extension project, but not register it with CloudFormation, use the `--dry-run` option for the `submit` command\.

You must register your extension in each region in which you want to use it\.

Use the [ListTypes](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ListTypes.html) action for summary information about types that have been registered with CloudFormation, and the [DescribeType](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeType.html) action for detailed information about specific registered resource type or resource type version\.

## Resource type provisioning<a name="resource-type-register-provision-type"></a>

During registration, CloudFormation examines which resource handlers have been implemented for the resource\. The handlers implemented determine what provisioning actions CloudFormation takes with respect to the resource during various stack operations\.
+ If the resource type does not contain `create`, `read`, and `delete` handlers, CloudFormation cannot actually provision the resource\.
+ If the resource type does not contain an `update` handler, CloudFormation cannot update the resource during stack update operations, and will instead replace it\.

## Extension versions and scope<a name="resource-type-register-versions"></a>

When you register an extension, you are actually registering a specific *version* of that extension\. You can register multiple versions of an extension, and specify which version you want to use\. Use the [SetTypeDefaultVersion](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_SetTypeDefaultVersion.html) action to specify the default version of an extension\. The default version of an extension will be used in CloudFormation operations\.

Any extension you register is only visible and usable within the account\(s\) in which you register it\.

## Deregistering extensions and extension versions<a name="resource-type-register-deregister"></a>

To remove an extension or extension version from active use in CloudFormation, you must *deregister* it using the [DeregisterType](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DeregisterType.html) action\. If an extension or extension version is deregistered, it can no longer be used in CloudFormation operations\.

You can deregister a specific extension version, or the extension as a whole\. To deregister an extension, you must individually deregister all registered versions of that extension\. If an extension has only a single registered version, deregistering that version results in the extension itself being deregistered\. You cannot deregister the default version of an extension, unless it is the only registered version of that extension, in which case the extension itself is deregistered as well\.

Deregistering an extension or extension version deregisters it in all regions\.

You cannot deregister an extension using the CloudFormation console\.
