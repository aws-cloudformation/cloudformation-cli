# What is the CloudFormation Command Line Interface?<a name="what-is-cloudformation-cli"></a>

The CloudFormation Command Line Interface \(CLI\) is an open\-source tool that enables you to develop and test AWS and third\-party extensions, such as resource types or modules, and register them for use in AWS CloudFormation\. The CloudFormation CLI provides a consistent way to model and provision both AWS and third\-party extensions through CloudFormation\. It includes commands to enable each step of creating your extensions\. 

An extension is an artifact, registered in the CloudFormation Registry, which augments the functionality of CloudFormation in a native manner\. Extensions can be written by Amazon, APN partners, Marketplace sellers, and the developer community\.

You can use the CloudFormation CLI to register extensions—both those you create yourself, as well as ones shared with you—with the CloudFormation registry\. This enables you to use CloudFormation capabilities to create, provision, and manage these custom types in a safe and repeatable manner, just as you would any AWS resource\. For more information on the CloudFormation registry, see [Using the CloudFormation registry](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/registry.html) in the *CloudFormation User Guide*\.

## Setting up your environment for developing extensions<a name="resource-type-setup"></a>

Before you can develop extensions, you'll need to set up your developer environment, including the CloudFormation CLI\.

Currently, plugins are available for the following languages:
+ Go
+ Java
+ Python

Or, if you're using another language, you can install the CloudFormation CLI directly\.

### Setting up your environment \(macOS\)<a name="resource-type-setup-java"></a>

#### Prerequisites<a name="resource-type-setup-java-prereqs"></a>
+ Python version 3\.6 or above
+ [AWS Command Line Interface](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-using-cli.html) for access to `aws cloudformation` commands\.
+ Your choice of IDE

  The [Walkthrough: Develop a resource type](resource-type-walkthrough.md) walkthrough uses the Community Edition of the [IntelliJ IDEA](https://www.jetbrains.com/idea/)\.
+ [AWS Serverless Application Model Command Line Interface](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) \(AWS SAM CLI\)
**Note**  
[Installing the AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install-mac.html) requires Docker as a prerequisite for testing your resource type locally\.

Complete the following steps:

1. Install Homebrew

   First, install [Homebrew](https://brew.sh/), an open\-source package manager for macOS\. You'll use Homebrew to install additional development requirements\.

1. Next, use Homebrew to install Python and the AWS Command Line Interface \(AWS CLI\)\.

   ```
   $ brew update
   $ brew install python awscli
   ```

#### Installing the CloudFormation CLI and plugins \(macOS\)<a name="resource-type-setup-java-steps"></a>

Use the Python Package Index \(PyPI\) to install the development plugin for the language of your choice\. Installing any of the plugins listed below also installs the CloudFormation CLI\. For full installation instructions, refer to the appropriate plugin repository\.


**Available Language Plugins**  

|  Language  |  Plugin Status  |  GitHub Location  |  PyPI Installation  | 
| --- | --- | --- | --- | 
|  Go  |  General Availability  |  [cloudformation\-cli\-go\-plugin](https://github.com/aws-cloudformation/cloudformation-cli-go-plugin/)  |  `cloudformation-cli-go-plugin`  | 
|  Java  |  General Availability  |  [cloudformation\-cli\-java\-plugin](https://github.com/aws-cloudformation/cloudformation-cli-java-plugin/)  |  `cloudformation-cli-java-plugin`  | 
|  Python  |  General Availability  |  [cloudformation\-cli\-python\-plugin](https://github.com/aws-cloudformation/cloudformation-cli-python-plugin/)  |  `cloudformation-cli-python-plugin`  | 

### Upgrading to CFN\-CLI 2\.0<a name="resource-type-setup-upgrade"></a>

If you have developed resource types using the CFN\-CLI 1\.0, we recommend you update to CFN\-CLI 2\.0 and rebuild those types\. Upgrading involves updating the CFN\-CLI, as well as any language plugins you are using, but does not require any changes to your resource type solution itself\.

Enhancements in CFN\-CLI 2\.0 include:
+ Increased resource payload limit, from 8 kb to 6 mb\.
+ Increased resource stabilization time, from 12 hours to 36 hours, or 48 hours if you are using a stack role to consume the resource\.
+ Improved resource stability, with improved retry strategy and fail\-fast\.

**To upgrade CFN\-CLI 2\.0 and the CloudFormation Provider Development Toolkit Go Plugin**

1. Upgrade the Go Plugin using the following command:

   ```
   pip3 install --upgrade cloudformation-cli-go-plugin
   ```

1. Update the Go plugin in the `go.mod` file\.

   ```
   go get -u github.com/aws-cloudformation/cloudformation-cli-go-plugin 
   ```

1. To update a resource type to use the CFN\-CLI 2\.0, build and register a new version of the resource using the following command:

   ```
   make
   cfn submit --set-default
   ```

**To upgrade CFN\-CLI 2\.0 and the CloudFormation Provider Development Toolkit Java Plugin**

1. Upgrade the Java Plugin using the following command:

   ```
   pip3 install --upgrade cloudformation-cli-java-plugin
   ```

1. Update Java plugin in maven pom\.xml to 2\.0\.0

   ```
   <dependency>
     <groupId>software.amazon.cloudformation</groupId>
     <artifactId>aws-cloudformation-rpdk-java-plugin</artifactId>
     <version>2.0.0</version>
   </dependency>
   ```

1. To update a resource type to use the CFN\-CLI 2\.0, build and register a new version of the resource using the following command:

   ```
   mvn package
   cfn submit --set-default
   ```

**To upgrade CFN\-CLI 2\.0 and the CloudFormation Provider Development Toolkit Python Plugin**

1. Upgrade the Python Plugin using the following command:

   ```
   pip3 install cloudformation-cli-python-plugin
   ```

1. To update a resource type to use the CFN\-CLI 2\.0, build and register a new version of the resource using the following command:

   ```
   cfn submit --set-default
   ```