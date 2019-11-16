# Resource Provider FAQ<a name="resource-type-faq"></a>

Below are some Frequently Asked Questions about resource provider development\.

## Updates<a name="resource-type-faq-updates"></a>
+ **Q: My service API implements Update actions as an Upsert, can I implement my CloudFormation resource provider in this way?**

  **A:** No, CloudFormation requires that `update` actions to a non\-existing resource always throw a `ResourceNotFoundException`\.

## Schema Development<a name="resource-type-faq-schema"></a>
+ **Q: How can I re\-use existing schemas, or establish relationships to other resource types in my schema?**

  **A:** Relationships and re\-use are established using JSON Pointers\. These are implemented using the `$ref` keyword in your resource provider schema\. Refer to [Modeling Resource Providers for Use in AWS CloudFormation ](resource-type-model.md) for more information\.

## Permissions and Authorization<a name="resource-type-faq-permissions"></a>
+ **Q: Why am I getting an `AccessDeniedException` for my AWS API calls?**

  **A:** If you are seeing errors in your logs related to AccessDeniedException for a Lambda Execution Role like

  ```
  A downstream service error occurred in a CREATE action on a AWS::MyService::MyResource: com.amazonaws.services.logs.model.AWSLogsException: User: arn:aws:sts::123456789012:assumed-role/UluruResourceHandlerLambdaExecutionRole-123456789012pdx/AWS-MYService-MyResource-Handler-1h344teffe is not authorized to perform: some:ApiCall on resource: some-resource (Service: AWSLogs; Status Code: 400; Error Code: AccessDeniedException; Request ID: 36af0cec-a96a-11e9-b204-ddabexample)
  ```

  This is an indication that you are attempting to create and invoke AWS APIs using the default client, which is injected with environment credentials\.

  For resource providers, you should use the passed\-in `AmazonWebServicesClientProxy` object to make AWS API calls, as in the following example\.

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

  **A:** For non\-AWS API calls which require authentication and authorization, you should create properties in your resource provider which contain the credentials\. Define these properties in the resource provider schema as `writeOnlyProperties`\.

  Users can then provide their own credentials through their CloudFormation templates\. We encourage the use of [dynamic references](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html) in CloudFormation templates, which can use AWS Secrets Manager to fetch credentials at runtime\.

## Provider Development<a name="resource-type-faq-dev"></a>
+ **Q: Can I share functionality between resource by adding common functionality to the `BaseHandler`?**

  **A:** Because the `BaseHandler` is code\-generated, it cannot be edited\.
+ **Q: For Java development, is there a way to include multiple resources in a single maven project?**

  **A:** Not currently\. For security and manageability, the CloudFormation Registry registers each resource provider as a separate, versioned, type\. You could still share code through a shared package\. Ideally, the wrapper layer does most of the boilerplate\. If you see a need for more boilerplate, we would like to know how we can improve for that use case rather than combine types in a package, so please reach out to the team\.
+ **Q: Will `software.amazon.cloudformation.proxy.Logger` have debug/info/warning/error levels/?**

  **A:** Currently, all log messages are emitted to AWS CloudWatch, which has no built\-in concept of log levels\.

## Testing<a name="resource-type-faq-test"></a>
+ **Q: For testing, when should I use `sam local invoke`, `cfn test` and `mvn test`?**

  **A:** Use the various test capabilities for the test scenarios described below\.
  + `sam local invoke`: Creating custom integration test by passing in custom CloudFormation payloads and isolate specific handlers\.
  + `cfn test`: Contract tests meant to cycle through CRUDL actions and ideally leave in a clean state \(if tests pass\)\.
  + `mvn test`: Used for Unit testing\. The goal is to confirm that each method/unit of the resource performs as intended\. It also helps to ensure that you have enough code coverage\. We expect unit tests to mock dependencies and not create real resources\.

## Deployment<a name="resource-type-faq-deploy"></a>
+ **Q: Is the provider interface guaranteed to be stable?**

  **A:** The communication protocol between CloudFormation and your provider resource package is subject to change\. However this will be done in a backwards\-compatible way, using versioned interfaces\. This will be invisible to you as a developer and is managed as part of the CloudFormation managed platform\.

  The interface that your handlers implement inside your package is expected to be stable\. We may introduce improvements, such as security fixes or other changes to the package, but these will be done with versioned dependency or CloudFormation CLI updates\. You are not required to upgrade your packages in order to publish them, only to incorporate these improvements\.
