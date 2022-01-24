# Resource type FAQ<a name="resource-type-faq"></a>

Below are some Frequently Asked Questions about resource type development\.

## Updates<a name="resource-type-faq-updates"></a>
+ **Q: My service API implements Update actions as an Upsert, can I implement my CloudFormation resource type in this way?**

  **A:** No, CloudFormation requires that `update` actions to a non\-existing resource always throw a `ResourceNotFoundException`\.

## Schema development<a name="resource-type-faq-schema"></a>
+ **Q: How can I re\-use existing schemas, or establish relationships to other resource types in my schema?**

  **A:** Relationships and re\-use are established using JSON Pointers\. These are implemented using the `$ref` keyword in your resource type schema\. Refer to [Modeling resource types for use in AWS CloudFormation](resource-type-model.md) for more information\.

## Permissions and authorization<a name="resource-type-faq-permissions"></a>
+ **Q: Why am I getting an `AccessDeniedException` for my AWS API calls?**

  **A:** If you are seeing errors in your logs related to AccessDeniedException for a Lambda Execution Role like

  ```
  A downstream service error occurred in a CREATE action on a AWS::MyService::MyResource: com.amazonaws.services.logs.model.AWSLogsException: User: arn:aws:sts::123456789012:assumed-role/UluruResourceHandlerLambdaExecutionRole-123456789012pdx/AWS-MYService-MyResource-Handler-1h344teffe is not authorized to perform: some:ApiCall on resource: some-resource (Service: AWSLogs; Status Code: 400; Error Code: AccessDeniedException; Request ID: 36af0cec-a96a-11e9-b204-ddabexample)
  ```

  This is an indication that you are attempting to create and invoke AWS APIs using the default client, which is injected with environment credentials\.

  For resource types, you should use the passed\-in `AmazonWebServicesClientProxy` object to make AWS API calls, as in the following example\.

  ```
  SesClient client = ClientBuilder.getClient();
  final CreateConfigurationSetRequest createConfigurationSetRequest =
      CreateConfigurationSetRequest.builder()
          .configurationSet(ConfigurationSet.builder()
              .name(model.getName())
              .build())
          .build();
  proxy.injectCredentialsAndInvokeV2(createConfigurationSetRequest, client::createConfigurationSet);
  ```
+ **Q: How do I specify credentials for non\-AWS API calls?**

  **A:** For non\-AWS API calls which require authentication and authorization, you should create properties in your resource type which contain the credentials\. Define these properties in the resource type schema as `writeOnlyProperties`\.

  Users can then provide their own credentials through their CloudFormation templates\. We encourage the use of [dynamic references](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html) in CloudFormation templates, which can use AWS Secrets Manager to fetch credentials at runtime\.

## Resource type development<a name="resource-type-faq-dev"></a>
+ **Q: Can I share functionality between resource by adding common functionality to the `BaseHandler`?**

  **A:** Because the `BaseHandler` is code\-generated, it cannot be edited\.
+ **Q: For Java development, is there a way to include multiple resources in a single maven project?**

  **A:** Not currently\. For security and manageability, the CloudFormation Registry registers each resource type as a separate, versioned, type\. You could still share code through a shared package\. Ideally, the wrapper layer does most of the boilerplate\. If you see a need for more boilerplate, we would like to know how we can improve for that use case rather than combine types in a package, so please reach out to the team\.
+ **Q: Will `software.amazon.cloudformation.proxy.Logger` have debug/info/warning/error levels/?**

  **A:** Currently, all log messages are emitted to CloudWatch, which has no built\-in concept of log levels\.
+ **Q: Does CloudFormation have a sandbox environment I can use to test and experiment with my extensions?**

  **A:** Using extensions from your private registry in stacks created in your account is the same as using a sandbox environment\.

## Testing<a name="resource-type-faq-test"></a>
+ **Q: For testing, when should I use `sam local invoke`, `cfn test` and `mvn test`?**

  **A:** Use the various test capabilities for the test scenarios described below\.
  + `sam local invoke`: Creating custom integration test by passing in custom CloudFormation payloads and isolate specific handlers\.
  + `cfn test`: Contract tests meant to cycle through CRUDL actions and ideally leave in a clean state \(if tests pass\)\.
  + `mvn test`: Used for Unit testing\. The goal is to confirm that each method/unit of the resource performs as intended\. It also helps to ensure that you have enough code coverage\. We expect unit tests to mock dependencies and not create real resources\.
+ **Q: How do I get the latest changes for a contract test?**

  **A:** Run `pip install cloudformation-cli cloudformation-cli-<language>-plugin --upgrade`\.
+ **Q: Where can I find the code for contract tests?**

  **A:** You can find the code for the test suite at [https://github\.com/aws\-cloudformation/cloudformation\-cli/tree/master/src/rpdk/core/contract/suite](https://github.com/aws-cloudformation/cloudformation-cli/tree/master/src/rpdk/core/contract/suite)\.
+ **Q: How do I check which version of contract tests I’m running?**

  **A:** Run `pip freeze`\. The output shows the CloudFormation CLI version\. The list of all releases for the CloudFormation CLI can be found at [https://github\.com/aws\-cloudformation/cloudformation\-cli/releases](https://github.com/aws-cloudformation/cloudformation-cli/releases)\.
+ **Q: I found a bug in the contract tests\. How do I report it?**

  **A:** File a bug at [https://github\.com/aws\-cloudformation/cloudformation\-cli/issues](https://github.com/aws-cloudformation/cloudformation-cli/issues)\.
+ **Q: How can I contribute to the development of contract tests?**

  **A:** Follow [these steps](https://github.com/aws-cloudformation/cloudformation-cli#development) to install a virtual development environment on your local machine\.
+ **Q: Contract tests time out on my local machine\. How do I resolve this issue?**

  **A:** Contract tests assert that `create`, `update`, and `delete` handlers return progress events every 60 seconds, and that `read` and `list` handlers complete in 30 seconds\. If you see errors for tests timing out, you can increase the timeout by running contract tests with the following argument: `cfn test --enforce-timeout <value>`\. The value specified is the new timeout threshold for the `read` and `list` handlers\. The new threshold for the `create`, `update`, and `delete` handlers is double the value specified\.
+ **Q: How do I run one contract test at a time?**

  **A:** You can run one contract test by running the following command: `cfn test -- -k <test-name>`\.
+ **Q: How do I define input files for contract tests?**

  **A:** [Specifying input data for use in contract tests](resource-type-test.md#resource-type-test-input-data) describes how to pass an input for contract tests and what each file should contain\.
+ **Q: How do I fix the `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)` error?**

  **A:** This exception message indicates that you might be running out of memory or time\. Add the following lines under `Globals` in the `template.yaml` file in your code package\.

  ```
  Globals:
    Function:
      Timeout: 180
      MemorySize: 256
  ```
+ **Q: Why do create operations fail when the `primaryIdentifier` is null?**

  **A:** The `create` handler should return the `primaryIdentifier` in the model\. If the `primaryIdentifier` for your resource is a read\-only property, you can update the returned model with the property or invoke the `read` handler in your `create` handler\.
+ **Q: Some tests fail because the input is not equal to the output\. How do I fix this?**

  **A:** Input\-output comparisons check that all properties are exactly equal, except for read\-only properties, write\-only properties, defaults, `insertionOrder`, and `uniqueItems`\.
+ **Q: Can the `update` handler update create\-only properties?**

  **A:** No\. The `update` handler cannot update create\-only properties\. These properties should remain the same in `update` models\.
+ **Q: Why does my `delete`/`read` handler fail with a `NotFound` or `InvalidRequest` error code?**

  **A:** Ensure that your input to these handlers is correct\. The `delete` and `read` handlers should be successfully invoked with just the `primaryIdentifier`\. The `read` handler can also be invoked with `additionalIdentifiers`\.
+ **Q: Why do delete operations fail when `resourceModel` is not null?**

  **A:** The `delete` handler should not return a model when successful\. You need to redact the model from the returned progress event\.
+ **Q: All of my properties are marked as create\-only properties\. Why do the `update` contract tests keep running and failing?**

  **A:** Remove the `update` block from the `handlers` section in your schema file\.
+ **Q: How do I fix permission issues during test execution?**

  **A:** Check the exception message to see which permissions are missing\. Add these permissions to `ExecutionRole` in the `resource-role.yaml` file in your code package\.

## Deployment<a name="resource-type-faq-deploy"></a>
+ **Q: Is the resource type interface guaranteed to be stable?**

  **A:** The communication protocol between CloudFormation and your resource type package is subject to change\. However this will be done in a backwards\-compatible way, using versioned interfaces\. This will be invisible to you as a developer and is managed as part of the CloudFormation managed platform\.

  The interface that your handlers implement inside your package is expected to be stable\. We may introduce improvements, such as security fixes or other changes to the package, but these will be done with versioned dependency or CloudFormation CLI updates\. You are not required to upgrade your packages in order to publish them, only to incorporate these improvements\.
