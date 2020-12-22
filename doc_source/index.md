# CloudFormation Command Line Interface User Guide for Extension Development

-----
*****Copyright &copy; 2020 Amazon Web Services, Inc. and/or its affiliates. All rights reserved.*****

-----
Amazon's trademarks and trade dress may not be used in 
     connection with any product or service that is not Amazon's, 
     in any manner that is likely to cause confusion among customers, 
     or in any manner that disparages or discredits Amazon. All other 
     trademarks not owned by Amazon are the property of their respective
     owners, who may or may not be affiliated with, connected to, or 
     sponsored by Amazon.

-----
## Contents
+ [What is the CloudFormation Command Line Interface?](what-is-cloudformation-cli.md)
+ [Creating resource types](resource-types.md)
   + [Modeling resource types for use in AWS CloudFormation](resource-type-model.md)
      + [Resource type schema](resource-type-schema.md)
      + [Patterns for modeling your resource types](resource-type-howtos.md)
   + [Developing resource types for use in AWS CloudFormation Templates](resource-type-develop.md)
      + [Testing resource types using contract tests](resource-type-test.md)
         + [Resource type handler contracts](resource-type-test-contract.md)
         + [Handler error codes](resource-type-test-contract-errors.md)
         + [ProgressEvent object schema](resource-type-test-progressevent.md)
      + [Progress chaining, stabilization and callback pattern](resource-type-develop-stabilize.md)
   + [Registering resource types for use in AWS CloudFormation templates](resource-type-register.md)
   + [Walkthrough: Develop a resource type](resource-type-walkthrough.md)
   + [Resource type FAQ](resource-type-faq.md)
+ [Developing modules](modules.md)
   + [Module structure](modules-structure.md)
   + [Develop a module using the CFN-CLI](modules-develop.md)
+ [CloudFormation CLI command reference](resource-type-cli.md)
   + [Global parameters](resource-type-cli-global-parameters.md)
   + [init](resource-type-cli-init.md)
   + [generate](resource-type-cli-generate.md)
   + [validate](resource-type-cli-validate.md)
   + [invoke](resource-type-cli-invoke.md)
   + [test](resource-type-cli-test.md)
   + [submit](resource-type-cli-submit.md)
+ [Document History for User Guide](doc-history.md)
+ [AWS glossary](glossary.md)