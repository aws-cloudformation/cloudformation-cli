# Publishing your extension in multiple Regions using AWS CloudFormation StackSets<a name="publish-extension-stacksets"></a>

Because CloudFormation is a regional service, you must repeat each required step to publish your extension to the public registry in all Regions you would like your extension to be available in\. However, with the use of CloudFormation resources, you can leverage AWS CloudFormation StackSets to publish your extensions globally in fewer steps\.

For more information about AWS CloudFormation StackSets, see [Working with AWS CloudFormation StackSets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html) in the *AWS CloudFormation User Guide*\.

**Important**  
While AWS CloudFormation is available in many Regions worldwide, our public registry is not supported in China \(cn\-north\-1 and cn\-northwest\-1\) or GovCloud \(us\-gov\-east\-1 and us\-gov\-west\-1\) Regions\. Any stack instances created using StackSets should only target the supported Regions\.

## Prerequisites for using AWS CloudFormation StackSets<a name="publish-extension-stacksets-prereqs"></a>

Before using StackSets, you must complete prerequisites depending on which management policy you want to use for your stack sets\. 
+ Stack sets with self\-managed permissions require that you create IAM roles in the necessary admin and target accounts\. If you intend to publish a type across multiple Regions from the same publisher account, you should create the roles in the same account\.
+ Stack sets with service\-managed permissions make use of AWS Organizations and thus require that you enable trusted access to AWS Organizations\.

For detailed instructions to set up the required permissions, see [Prerequisites for stack set operations](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-prereqs.html)\.

## Using StackSets to publish in multiple Regions for the first time<a name="publish-extension-stacksets-new"></a>

The example templates in this section publish extensions for the first time to the public registry\. They contain the following CloudFormation resource types to mimic the workflow of publishing an extension in a single Region:
+ `AWS::CloudFormation::ResourceVersion` or `AWS::CloudFormation::ModuleVersion` \- Registers a new version for a private type\.
+ `AWS::CloudFormation::ResourceDefaultVersion` or `AWS::CloudFormation::ModuleDefaultVersion` \- Sets the new version to the type’s default version\. The default version is used for publishing\.
+ `AWS::CloudFormation::Publisher` \- Registers the calling account as a publisher with AWS Marketplace\. This functionality is idempotent, meaning that once you’ve registered as a publisher, this resource does not get updated\.
+ `AWS::CloudFormation::PublicTypeVersion` \- Tests the new version and publishes it to the public registry\.

For more details about each type, including settings you can modify, see the [AWS CloudFormation resource type reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/AWS_CloudFormation.html) in the *AWS CloudFormation User Guide*\.

**Note**  
The same publishing restrictions apply when you use StackSets to publish extensions globally, including agreeing to the [Terms and Conditions for AWS CloudFormation Registry Publishers](https://cloudformation-registry-documents.s3.amazonaws.com/Terms_and_Conditions_for_AWS_CloudFormation_Registry_Publishers.pdf) before registering as a publisher and ensuring your extension passes all test requirements before successfully publishing\.

The following example template publishes a resource type across Regions with StackSets\.

```
AWSTemplateFormatVersion: "2010-09-09"
Description: Registers and sets a new default resource version, registers the account as a publisher, and publishes the resource to the public registry.
Parameters:
  SchemaPackageURL:
    Description: URL to S3::Bucket that contains the resource project package 
    Type: String
Resources:
  PrivateResourceVersion: 
    Type: AWS::CloudFormation::ResourceVersion
    Properties:
      SchemaHandlerPackage: !Ref SchemaPackageURL 
      TypeName: MyOrg::MyService::MyType 
  ResourceDefaultVersion:    
    Type: AWS::CloudFormation::ResourceDefaultVersion
    DependsOn: PrivateResourceVersion
    Properties:
      TypeVersionArn: !Ref PrivateResourceVersion
  Publisher:
    Type: AWS::CloudFormation::Publisher
    DependsOn: ResourceDefaultVersion
    Properties:
      AcceptTermsAndConditions: true
  PublishedResource:     
    Type: AWS::CloudFormation::PublicTypeVersion
    DependsOn: Publisher
    Properties:
      Type: RESOURCE
      TypeName: MyOrg::MyService::MyType
```

The following example template publishes a module across Regions with StackSets\.

```
AWSTemplateFormatVersion: "2010-09-09"
Description: Registers and sets a new default module version, registers the account as a publisher, and publishes the module to the public registry with the given public version.
Parameters:
  VersionToPublish:
    Description: Version number for published version, e.g. 1.2.3
    Type: String
    Default: AWS::NoValue
  FirstTimePublishing:
    Description: Indicate if this is the first time publishing this extension in the targeted region. 
    Type: String
    AllowedValues:
      - true
      - false
  SchemaPackageURL:
    Description: URL to S3::Bucket that contains the resource project package 
    Type: String
Conditions:
  IsFirstTimePublishing: !Equals
    - !Ref FirstTimePublishing
    - true    
Resources:
  PrivateModuleVersion:
    Type: AWS::CloudFormation::ModuleVersion
    Properties:
      ModulePackage: !Ref SchemaPackageURL 
      ModuleName: MyOrg::MyService::MyType::MODULE 
  ModuleDefaultVersion:    
    Type: AWS::CloudFormation::ModuleDefaultVersion 
    DependsOn: PrivateModuleVersion
    Properties:
      Arn: !Ref PrivateModuleVersion
  Publisher:
    Type: AWS::CloudFormation::Publisher
    DependsOn: ModuleDefaultVersion
    Properties:
      AcceptTermsAndConditions: true
  PublishedModule:      
    Type: AWS::CloudFormation::PublicTypeVersion
    DependsOn: Publisher
    Properties:
      Type: MODULE 
      TypeName: MyOrg::MyService::MyType::MODULE      
      PublicVersionNumber: 
        Fn::If:
        - IsFirstTimePublishing
        - Ref: AWS::NoValue
        - Ref: VersionToPublish
```

Note that for `AWS::CloudFormation::PublicTypeVersion` resources, `PublicVersionNumber` cannot be specified upon creation\. CloudFormation automatically publishes the first version of the extension with version number 1\.0\.0\.

As a publisher, you can choose to provide version numbers for new versions\. The second template above requires you to input whether it is your first time publishing the extension\. You can subsequently modify this by overriding parameters when updating the stack set\.

If you instead choose to omit the `PublicVersionNumber` property \(as shown in the first template above\), all publishing updates increment the minor version by 1\. For example, version 1\.0\.0 increments to version 1\.1\.0\. To publish a new patch or major version, you must explicitly specify a new version number\.

Once your template is created and validated, you can create a stack set and new stack instances for each Region you want to publish your extension in\. For more information about how to use AWS CloudFormation StackSets in the AWS CLI and AWS Management Console, see [Create a stack set](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-getting-started-create.html) in the *AWS CloudFormation User Guide*\.

## Using StackSets to update already published extensions<a name="publish-extension-stacksets-update"></a>

AWS CloudFormation StackSets allows you to customize each stack instance, meaning that you can use the same stack set to continuously update and maintain your published extensions\. If you’ve already published extensions to the public registry and wish to use StackSets to manage all future updates, you can bring them directly into the stack set *without* publishing a new version\.
+ If the extensions were registered, tested, and published using CloudFormation APIs, they first need to be imported into stacks\. For information about using resource import, see [Bringing existing resources into CloudFormation management](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resource-import.html)\.
+ If the extensions were managed in individual stacks or you’ve successfully imported them into stacks, the stacks need to be imported into the stack set\. For instructions, see [Importing a stack into AWS CloudFormation StackSets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-import.html)\.

You can use the following StackSets actions to update your published extensions:
+ [Adding stack instances](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stackinstances-create.html) to your stack set publishes your extensions in additional Regions\. If you add a stack instance in a Region you’ve already independently published to \(not using StackSets\), this brings the published extension into the stack set’s management\.
+ [Overriding parameters on existing stack instances](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stackinstances-override.html) allows you to update and publish new versions for your already published extensions at an individual level\. This can be used when you want to specify new version numbers when performing updates\.
+ [Updating your stack set](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-update.html) can be used to modify the existing template, add new stack instances, modify parameters, and perform other edits\. You can do this if you choose not to specify version numbers in your template, but later decide you want to provide them\.

For more information about how to use AWS CloudFormation StackSets, see [Working with AWS CloudFormation StackSets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html) in the *AWS CloudFormation User Guide*\.
