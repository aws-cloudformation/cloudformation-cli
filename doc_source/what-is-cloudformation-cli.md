# What is the CloudFormation Command Line Interface \(CLI\)?<a name="what-is-cloudformation-cli"></a>

The *CloudFormation Command Line Interface \(CLI\)* is an open\-source tool that enables you to develop and test AWS and third\-party extensions, such as resource types or modules, and register them for use in AWS CloudFormation\. The CloudFormation CLI provides a consistent way to model and provision both AWS and third\-party extensions through CloudFormation\. The CloudFormation CLI includes commands to manage each step of creating your extensions\. For more information on CloudFormation CLI commands see, [CloudFormation CLI reference](resource-type-cli.md)\.

An *extension* is an artifact, registered in the CloudFormation registry, which augments the functionality of CloudFormation in a native manner\. Extensions can be registered by Amazon, APN partners, AWS Marketplace sellers, and the developer community\.

You can use the CloudFormation CLI to register extensions – both those you create yourself, in addition to ones shared with you – with the CloudFormation registry\. Extensions enable CloudFormation capabilities to create, provision, and manage these custom types in a safe and repeatable manner, just as you would any AWS resource\. For more information on the CloudFormation registry, see [Using the CloudFormation registry](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/registry.html) in the *CloudFormation User Guide*\.

## Setting up your environment for developing extensions<a name="resource-type-setup"></a>

Before you can develop extensions, you'll need to set up your developer environment, including the CloudFormation CLI\.

Currently, plugins are available for the following languages:
+ Go
+ Java
+ Python
+ TypeScript

Or, if you're using another language, you can install the CloudFormation CLI directly\.

### Setting up your environment<a name="resource-type-setup-java"></a>

#### Prerequisites<a name="resource-type-setup-java-prereqs"></a>
+ Python version 3\.6 or above\.
+ [CloudFormation CLI command reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-using-cli.html) for access to `aws cloudformation` commands\.
+ Your choice of IDE\.

  The [Walkthrough: Develop a resource type](resource-type-walkthrough.md) walkthrough uses the Community Edition of the [IntelliJ IDEA](https://www.jetbrains.com/idea/)\.
+ [AWS Serverless Application Model Command Line Interface](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) \(AWS SAM CLI\)\.
**Note**  
[Installing the AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install-mac.html) requires Docker as a prerequisite for testing your resource type locally\.

##### Installing the CloudFormation CLI<a name="installing-cfn-cli-python"></a>

The CloudFormation CLI can be installed using pip from the [Python Package Index \(PyPI\)](https://pypi.org/)\.
+ Resource types – Requires at least one language plugin\.
+ Module types – Language plugins aren't required\.

The language plugins are also available on PyPI\. Use the following command to install all the language plugins at once\.

```
pip install cloudformation-cli cloudformation-cli-java-plugin cloudformation-cli-go-plugin cloudformation-cli-python-plugin cloudformation-cli-typescript-plugin
```

##### \(macOS\) Installing CloudFormation CLI<a name="installing-cfn-cli-homebrew"></a>

**Install Homebrew**

1. Install [Homebrew](https://brew.sh/), an open\-source package manager for macOS\. You'll use Homebrew to install additional development requirements\.

1. Use Homebrew to install Python and the CloudFormation Command Line Interface \(CLI\)\.

   ```
   $ brew update
   $ brew install cloudformation-cli
   ```

#### Installing the CloudFormation CLI and plugins<a name="resource-type-setup-java-steps"></a>

Use the Python Package Index \(PyPI\) to install the development plugin for the language of your choice\. Installing any of the plugins listed below also installs the CloudFormation CLI\. For full installation instructions, refer to the appropriate plugin repository\.


**Available Language Plugins**  

|  Language  |  Plugin status  |  GitHub location  |  PyPI installation  | 
| --- | --- | --- | --- | 
|  Go  |  General availability  |  [cloudformation\-cli\-go\-plugin](https://github.com/aws-cloudformation/cloudformation-cli-go-plugin/)  |  `cloudformation-cli-go-plugin`  | 
|  Java  |  General availability  |  [cloudformation\-cli\-java\-plugin](https://github.com/aws-cloudformation/cloudformation-cli-java-plugin/)  |  `cloudformation-cli-java-plugin`  | 
|  Python  |  General availability  |  [cloudformation\-cli\-python\-plugin](https://github.com/aws-cloudformation/cloudformation-cli-python-plugin/)  |  `cloudformation-cli-python-plugin`  | 
|  TypeScript  |  General availability  |  [cloudformation\-cli\-typescript\-plugin](https://github.com/aws-cloudformation/cloudformation-cli-typescript-plugin/)  |  `cloudformation-cli-typescript-plugin`  | 

### Upgrading to CFN\-CLI 2\.0<a name="resource-type-setup-upgrade"></a>

If you have developed resource types using the CFN\-CLI 1\.0, we recommend you update to CFN\-CLI 2\.0 and rebuild those types\. Upgrading involves updating the CloudFormation CLI, in addition to any language plugins you are using, but doesn't require any changes to your resource type solution itself\.

Enhancements in CFN\-CLI 2\.0 include:
+ Increased resource payload limit, from 8 KB to 6 MB\.
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

1. Update Java plugin in maven pom\.xml to 2\.0\.0\.

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
