# Developing modules<a name="modules"></a>

*Module*s are a way for you to package resource configurations for inclusion across stack templates, in a transparent, manageable, and repeatable way\. Use modules to encapsulate common service configurations and best practices as modular, customizable building blocks that users can then take and include in their stack templates\. Modules enable you to capture and disseminate resource configurations that incorporate best practices, expert domain knowledge, and accepted guidelines \(for areas such as security, compliance, governance, and industry regulations\)\. Users can then include the module in their template without having to acquire deep knowledge of the intricacies of the resource implementation\.

For example, a domain expert in networking could create a module that contains built\-in security groups and ingress/egress rules that adhere to security guidelines\. A user could then include that module in their template to provision secure networking infrastructure in their stack, without having to spend time figuring out how VPCs, subnets, security groups, and gateways work\. And because modules are versioned, if security guidelines change over time, the module author can create a new version of the module that incorporates those changes\.

A module can contain:
+ Template sections, including resources to be provisioned from the module, along with any associated data, such as outputs or conditions\. Modules can also contain other modules\.
+ Any *module parameters*, which enable you to specify custom values whenever the module is used\.

Characteristics of modules include:
+ *Predictability*: Because a module must adhere to its schema, the resources and other outputs provisioned from the module are predictable\.
+ *Reusability*: Develop a module once, then reuse it across multiple templates and accounts
+ *Traceability*: CloudFormation retains knowledge of which resources in a stack were provisioned from a module, enabling users to trace the source of resource changes\.
+ *Manageability*: Once you've registered a module, you can manage it through the CloudFormation registry, including versioning and account and region availability\.

Users are able to register modules as private types in the CloudFormation registry for use in their accounts\.

To use a module, users include it in their template as they would an individual resource, including specifying any necessary parameters for the module\. When users initiate a stack operation, CloudFormation generates a processed template that resolves any included modules into the appropriate resources\.

Users can use [change sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html) to preview the resources to be added or updated before initiating the stack operation\.

For more information on using a module in a template, see [Using modules to encapsulate and reuse resource configurations](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/modules.html) in the *CloudFormation User Guide*\.