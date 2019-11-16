# Registering Resource Providers for Use in AWS CloudFormation Templates<a name="resource-type-register"></a>

Once you've completed developing your resource provider, you'll need to *register* it with CloudFormation in order to make it available for use in CloudFormation operations\. From the CloudFormation CLI, use the `[submit](resource-type-cli-submit.md)` command to register your resource with CloudFormation\. The `submit` command does the following:
+ Validates the resource schema\.
+ Packages up the resource project files and uploads them to CloudFormation\.

  This includes the source code for your resource handlers\. These resource handlers run within the CloudFormation service account\.
+ Runs the unit and contract tests defined in the resource project\.
+ Determines which handlers have been specified for the resource, to determine how CloudFormation provisions the resource\.
+ Returns a *registration token* that you can use with the [DescribeTypeRegistration](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeTypeRegistration.html) action to track the status of the registration request\.

To validate and package your resource project, but not register it with CloudFormation, use the `--dry-run` option for the `submit` command\.

You can also register your resource directly using the [RegisterType](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_RegisterType.html) action\.

You must register a resource in each region in which you want to use it\.

Use the [ListTypes](https://docs.aws.amazon.com/AWSCloudFormationApiDoc/build/server-root/AWSCloudFormation/latest/APIReference/API_ListTypes.html) action for summary information about types that have been registered with CloudFormation, and the [DescribeType](https://docs.aws.amazon.com/AWSCloudFormationApiDoc/build/server-root/AWSCloudFormation/latest/APIReference/API_DescribeType.html) action for detailed information about specific registered resource provider or resource provider version\.

## Resource Provider Versions<a name="resource-type-register-versions"></a>

When you register a resource provider, you are actually registering a specific *version* of that resource provider\. You can register multiple versions of a resource provider, and specify which version you want to use\.

Use the [SetTypeDefaultVersion](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_SetTypeDefaultVersion.html) action to specify the default version of a type\. The default version of a resource provider will be used in CloudFormation operations\.

## Resource Provider Scope<a name="resource-type-register-scope"></a>

Any resource provider you register is only visible and usable within the account\(s\) in which you register it\.

## Resource Provider Provisioning<a name="resource-type-register-provision-type"></a>

During registration, CloudFormation examines which resource handlers have been implemented for the resource\. The handlers implemented determine what provisioning actions CloudFormation takes with respect to the resource during various stack operations\.
+ If the resource provider does not contain `create`, `read`, and `delete` handlers, CloudFormation cannot actually provision the resource\.
+ If the resource provider does not contain an `update` handler, CloudFormation cannot update the resource during stack update operations, and will instead replace it\.

## Deregistering Resource Providers and Provider Versions<a name="resource-type-register-deregister"></a>

To remove a resource provider or provider version from active use in CloudFormation, you must *deregister* it using the [DeregisterType](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DeregisterType.html) action\. If a type or type version is deregistered, it can no longer be used in CloudFormation operations\.

You can deregister a specific resource provider version, or the resource provider as a whole\. To deregister a type, you must individually deregister all registered versions of that type\. If a type has only a single registered version, deregistering that version results in the type itself being deregistered\. You cannot deregister the default version of a type, unless it is the only registered version of that type, in which case the type itself is deregistered as well\.

Deregistering a resource provider or resource provider version deregisters it in all regions\.

You cannot deregister a resource using the CloudFormation console\.
