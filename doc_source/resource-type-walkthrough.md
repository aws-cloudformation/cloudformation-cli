# Walkthrough: Develop a Resource Provider<a name="resource-type-walkthrough"></a>

In this walkthrough, we'll use the CloudFormation CLI to create a sample resource provider, `Custom::Testing::WordPress`\. This includes modeling the schema, developing the handlers to testing those handlers, all the way to performing a dry run to get the resource provider ready to submit to the CloudFormation registry\. We'll be coding our new resource provider in Java, and using the `us-west-2` region\.

## Prerequisites<a name="resource-type-walkthrough-prereqs"></a>

For purposes of this walkthrough, it is assumed you have already set up the CloudFormation CLI and associated tooling for your Java development environment:

[Setting Up Your Environment for Developing Resource Providers](resource-type-setup.md)

## Create the Resource Provider Development Project<a name="resource-type-walkthrough-model"></a>

Before we can actually design and implement our resource provider, we'll need to generate a new resource type project, and then import it into our IDE\.

**Note**
This walkthrough uses the Community Edition of the [IntelliJ IDEA](https://www.jetbrains.com/idea/)\.

### Initiate the project<a name="resource-type-walkthrough-model-initiate"></a>

1. Use the `init` command to create your resource provider project and generate the files it requires\.

   ```
   $ cfn init
   Initializing new project
   ```

1. The `init` command launches a wizard that walks you through setting up the project, including specifying the resource name\. For this walkthrough, specify `Custom::Testing::WordPress`\.

   ```
   Enter resource type identifier (Organization::Service::Resource): Custom::Testing::WordPress
   ```

   The wizard then enables you to select the appropriate language plugin\. Currently, the only language plugin available is for Java:

   ```
   One language plugin found, defaulting to java
   ```

1. Finally, specify the package name\. For this walkthrough, use `com.custom.testing.wordpress`

   ```
   Enter a package name (empty for default 'com.custom.testing.wordpress'): com.custom.testing.wordpress
   Initialized a new project in /workplace/tobflem/custom-testing-wordpress
   ```

Intiating the project includes generating the files needed to develop the resource provider\. For example:

```
$ ls -1
README.md
custom-testing-wordpress.json
cfn
lombok.config
pom.xml
rpdk.log
src
target
template.yml
```

### Import the project into your IDE<a name="resource-type-walkthrough-model-import"></a>

In order to guarantee that any project dependencies are correctly resolved, you must import the generated project into your IDE with Maven support\.

For example, if you are using IntelliJ IDEA, you would need to do the following:

1. From the **File** menu, choose **New**, then choose **Project From Existing Sources**\.

1. Navigate to the project directory

1. In the **Import Project** dialog box, choose **Import project from external model** and then choose **Maven**\.

1. Choose **Next** and accept any defaults to complete importing the project\.

## Model the Resource Provider<a name="resource-type-walkthrough-model"></a>

When you initiate the resource provider project, an example resource provider schema file is included to help start you modeling your resource provider\. This is a JSON file named for your resource, and contains an example of a typical resource provider schema\. In the case of our example resource, the schema file is named `custom-testing-wordpress.json`\.

1. In your IDE, open `custom-testing-wordpress.json`\.

1. Paste the following schema in place of the default example schema currently in the file\.

   This schema defines a resource, `Custom::Testing::WordPress`, that provisions a WordPress site\. The resource itself contains four properties, only two of which can be set by users: `Name`, and `SubnetId`\. The other two properties, `InstanceId` and `PublicIp`, are read\-only, meaning they cannot be set by users, but will be assigned during resource creation\. Both of these properties also serve as identifiers for the resource when it is provisioned\.

   As we'll see later in the walkthrough, creating a WordPress site actually requires more information than represented in our resource model\. However, we'll be handling that information on behalf of the user in the code for the resource `create` handler\.

   ```
   {
     "typeName": "Custom::Testing::WordPress",
     "description": "An example resource that creates a website based on WordPress 5.2.2.",
     "sourceUrl": "The URL of the source code for this resource, if public.",
     "properties": {
       "Name": {
         "description": "A name associated with the website.",
         "type": "string",
         "pattern": "^[a-zA-Z0-9]{1,219}\\Z",
         "minLength": 1,
         "maxLength": 219
       },
       "SubnetId": {
         "description": "A subnet in which to host the website.",
         "pattern": "^(subnet-[a-f0-9]{13})|(subnet-[a-f0-9]{8})\\Z",
         "type": "string"
       },
       "InstanceId": {
         "description": "The ID of the instance that backs the WordPress site.",
         "type": "string"
       },
       "PublicIp": {
         "description": "The public IP for the WordPress site.",
         "type": "string"
       }
     },
     "required": [
       "Name",
       "SubnetId"
     ],
     "handlers": {
       "create": {
         "permissions": [
           "ec2:AuthorizeSecurityGroupIngress",
           "ec2:CreateSecurityGroup",
           "ec2:DeleteSecurityGroup",
           "ec2:DescribeInstances",
           "ec2:DescribeSubnets",
           "ec2:RunInstances"
         ]
       },
       "delete": {
         "permissions": [
           "ec2:DeleteSecurityGroup",
           "ec2:DescribeInstances",
           "ec2:TerminateInstances"
         ]
       }
     },
     "primaryIdentifier": [
       "/properties/PublicIp",
       "/properties/InstanceId"
     ],
     "readOnlyProperties": [
       "/properties/PublicIp",
       "/properties/InstanceId"
     ]
   }
   ```

1. Update the auto\-generated files in the resource provider package so that they reflect the changes we've made to the resource provider schema\.

   When we first initiated the resource provider project, the CloudFormation CLI generated supporting files and code for our resource provider\. Since we've made changes to the resource provider schema, we'll need to regenerate that code to ensure that it reflects the updated schema\. To do this, we use the generate command:

   ```
   $ cfn generate
   Generated files for Custom::Testing::WordPress
   ```
**Note**
When using Maven, as part of the build process the `generate` command is automatically run before the code is compiled\. So your changes will never get out of sync with the generated code\.
Be aware the CloudFormation CLI must be in a location Maven/the system can find\. For more information, see [Setting Up Your Environment for Developing Resource Providers](resource-type-setup.md)\.

## Implement the Resource Handlers<a name="resource-type-walkthrough-implement"></a>

Now that we have our resource provider schema specified, we can start implementing the behavior we want the resource provider to exhibit during each resource operation\. To do this, we'll have to implement the various event handlers, including:
+ Adding any necessary dependencies
+ Writing code to implement the various resource operation handlers\.

### Add Dependencies<a name="resource-type-walkthrough-implement-dependencies"></a>

To actually make WordPress handlers that call the associated EC2 APIs, we need to declare the AWS EC2 SDK as a dependency in Maven's pom\.xml file\. To enable this, we need to add a dependency on the [AWS SDK for Java](https://sdk.amazonaws.com/java/api/latest/software/amazon/awssdk/services/ec2/package-summary.html) to the project\.

1. In your IDE, open the project's `pom.xml` file\.

1. Add the following dependency in the `dependencies` section\.

   ```
   <dependency>
     <groupId>com.amazonaws</groupId>
     <artifactId>aws-java-sdk-ec2</artifactId>
     <version>1.11.606</version>
   </dependency>
   ```

   This artifact will be added by Maven from the [Maven Repository](https://mvnrepository.com/artifact/com.amazonaws/aws-java-sdk-logs)\.

For more information on how to add dependencies, see the [Maven documentation](https://maven.apache.org/guides/introduction/introduction-to-dependency-mechanism.html)\.

**Note**
Depending on your IDE, you may have to take additional steps for your IDE to include the new dependency\.
In IntelliJ IDEA, a dialog should appear to enable you to import these changes\. we recommend allowing automatic importing\.

### Implement the Create Handler<a name="resource-type-walkthrough-implement-create-handler"></a>

With the necessary dependency specified, we can now start writing the handlers that actually implement the resource's functionality\. For our example resource, we'll implement just the `create` and `delete` operation handlers\.

To create a WordPress site, our resource `create` handler will have to accomplish the following:
+ Gather and define inputs that we'll need to create the underlying AWS resources on behalf of the user\. These are details we're managing for them, since this is a very high\-level resource type\.
+ Create an EC2 instance using a special AMI vended by Bitnami from the AMI Marketplace that bootstraps WordPress\.
+ Create a security group that the instance will belong to so you can access the WordPress site from your browser\.
+ Change the security group rules to dictate what the networking rules are for web access to the WordPress site\.
+ If something goes wrong with creating the resource, attempt to delete the security group\.

#### Define the CallbackContext<a name="resource-type-walkthrough-implement-create-handler-context"></a>

Because our create handler is more complex than simply calling a single API, it takes some time to complete\. However, each handler times out after one minute\. To work around this issue, we'll write our handlers as state machines\. A handler can exit with one of three states: SUCCESS, IN\_PROGRESS, and FAILED\. To wait on stabilization of underlying resources, we can return an IN\_PROGRESS state with a CallbackContext\. The CallbackContext will hold details about the current state of the execution\. When we return an IN\_PROGRESS state and a CallbackContext, CloudFormation will re\-invoke the handler and pass the CallbackContext in with the request\. You can then make decisions based on what is included in the context\.

The CallbackContext is modeled as a POJO so you can define what information you want to pass between state transitions explicitly\.

1. In your IDE, open the `CallbackContext.java` file, located in the `src/main/java/com/custom/testing/wordpress` folder\.

1. Replace the entire contents of the `CallbackContext.java` file with the following code\.

   ```
   package com.custom.testing.wordpress;

   import com.amazonaws.services.ec2.model.Instance;

   import java.util.List;

   import lombok.AllArgsConstructor;
   import lombok.Builder;
   import lombok.Data;
   import lombok.NoArgsConstructor;

   @Builder(toBuilder = true)
   @Data
   @NoArgsConstructor
   @AllArgsConstructor
   public class CallbackContext {
       private Instance instance;
       private Integer stabilizationRetriesRemaining;
       private List<String> instanceSecurityGroups;
   }
   ```

#### Code the Create Handler<a name="resource-type-walkthrough-implement-create-handler-code"></a>

1. In your IDE, open the `CreateHandler.java` file, located in the `src/main/java/com/custom/testing/wordpress/CreateHandler.java` folder\.

1. Replace the entire contents of the `CreateHandler.java` file with the following code\.

   ```
   package com.custom.testing.wordpress;

   import software.amazon.cloudformation.proxy.AmazonWebServicesClientProxy;
   import software.amazon.cloudformation.proxy.Logger;
   import software.amazon.cloudformation.proxy.OperationStatus;
   import software.amazon.cloudformation.proxy.ProgressEvent;
   import software.amazon.cloudformation.proxy.ResourceHandlerRequest;
   import com.amazonaws.services.ec2.AmazonEC2;
   import com.amazonaws.services.ec2.AmazonEC2ClientBuilder;
   import com.amazonaws.services.ec2.model.AuthorizeSecurityGroupIngressRequest;
   import com.amazonaws.services.ec2.model.CreateSecurityGroupRequest;
   import com.amazonaws.services.ec2.model.DeleteSecurityGroupRequest;
   import com.amazonaws.services.ec2.model.DescribeInstancesRequest;
   import com.amazonaws.services.ec2.model.DescribeInstancesResult;
   import com.amazonaws.services.ec2.model.DescribeSubnetsRequest;
   import com.amazonaws.services.ec2.model.DescribeSubnetsResult;
   import com.amazonaws.services.ec2.model.Instance;
   import com.amazonaws.services.ec2.model.InstanceNetworkInterfaceSpecification;
   import com.amazonaws.services.ec2.model.IpPermission;
   import com.amazonaws.services.ec2.model.IpRange;
   import com.amazonaws.services.ec2.model.Reservation;
   import com.amazonaws.services.ec2.model.RunInstancesRequest;
   import com.amazonaws.services.ec2.model.Subnet;
   import com.amazonaws.services.ec2.model.Tag;
   import com.amazonaws.services.ec2.model.TagSpecification;

   import java.util.List;
   import java.util.UUID;

   public class CreateHandler extends BaseHandler<CallbackContext> {
       private static final String SUPPORTED_REGION = "us-west-2";
       private static final String WORDPRESS_AMI_ID = "ami-04fb0368671b6f138";
       private static final String INSTANCE_TYPE = "m4.large";
       private static final String SITE_NAME_TAG_KEY = "Name";
       private static final String AVAILABLE_INSTANCE_STATE = "running";
       private static final int NUMBER_OF_STATE_POLL_RETRIES = 60;
       private static final int POLL_RETRY_DELAY_IN_MS = 5000;
       private static final String TIMED_OUT_MESSAGE = "Timed out waiting for instance to become available.";

       private AmazonWebServicesClientProxy clientProxy;
       private AmazonEC2 ec2Client;

       @Override
       public ProgressEvent<ResourceModel, CallbackContext> handleRequest(
           final AmazonWebServicesClientProxy proxy,
           final ResourceHandlerRequest<ResourceModel> request,
           final CallbackContext callbackContext,
           final Logger logger) {

           final ResourceModel model = request.getDesiredResourceState();

           clientProxy = proxy;
           ec2Client = AmazonEC2ClientBuilder.standard().withRegion(SUPPORTED_REGION).build();
           final CallbackContext currentContext = callbackContext == null ?
                                                  CallbackContext.builder().stabilizationRetriesRemaining(NUMBER_OF_STATE_POLL_RETRIES).build() :
                                                  callbackContext;

           // This Lambda will continually be re-invoked with the current state of the instance, finally succeeding when state stabilizes.
           return createInstanceAndUpdateProgress(model, currentContext);
       }

       private ProgressEvent<ResourceModel, CallbackContext> createInstanceAndUpdateProgress(ResourceModel model, CallbackContext callbackContext) {
           // This Lambda will continually be re-invoked with the current state of the instance, finally succeeding when state stabilizes.
           final Instance instanceStateSoFar = callbackContext.getInstance();

           if (callbackContext.getStabilizationRetriesRemaining() == 0) {
               throw new RuntimeException(TIMED_OUT_MESSAGE);
           }

           if (instanceStateSoFar == null) {
               return ProgressEvent.<ResourceModel, CallbackContext>builder()
                   .resourceModel(model)
                   .status(OperationStatus.IN_PROGRESS)
                   .callbackContext(CallbackContext.builder()
                                                   .instance(createEC2Instance(model))
                                                   .stabilizationRetriesRemaining(NUMBER_OF_STATE_POLL_RETRIES)
                                                   .build())
                   .build();
           } else if (instanceStateSoFar.getState().getName().equals(AVAILABLE_INSTANCE_STATE)) {
               model.setInstanceId(instanceStateSoFar.getInstanceId());
               model.setPublicIp(instanceStateSoFar.getPublicIpAddress());
               return ProgressEvent.<ResourceModel, CallbackContext>builder()
                   .resourceModel(model)
                   .status(OperationStatus.SUCCESS)
                   .build();

           } else {
               try {
                   Thread.sleep(POLL_RETRY_DELAY_IN_MS);
               } catch (InterruptedException e) {
                   throw new RuntimeException(e);
               }
               return ProgressEvent.<ResourceModel, CallbackContext>builder()
                   .resourceModel(model)
                   .status(OperationStatus.IN_PROGRESS)
                   .callbackContext(CallbackContext.builder()
                                                   .instance(updatedInstanceProgress(instanceStateSoFar.getInstanceId()))
                                                   .stabilizationRetriesRemaining(callbackContext.getStabilizationRetriesRemaining() - 1)
                                                   .build())
                   .build();
           }
       }

       private Instance createEC2Instance(ResourceModel model) {
           final String securityGroupId = createSecurityGroupForInstance(model);
           final RunInstancesRequest runInstancesRequest = new RunInstancesRequest()
               .withInstanceType(INSTANCE_TYPE)
               .withImageId(WORDPRESS_AMI_ID)
               .withNetworkInterfaces(new InstanceNetworkInterfaceSpecification()
                                          .withAssociatePublicIpAddress(true)
                                          .withDeviceIndex(0)
                                          .withGroups(securityGroupId)
                                          .withSubnetId(model.getSubnetId()))
               .withMaxCount(1)
               .withMinCount(1)
               .withTagSpecifications(buildTagFromSiteName(model.getName()));

           try {
               return clientProxy.injectCredentialsAndInvoke(runInstancesRequest, ec2Client::runInstances)
                                 .getReservation()
                                 .getInstances()
                                 .stream()
                                 .findFirst()
                                 .orElse(new Instance());
           } catch (Throwable e) {
               attemptToCleanUpSecurityGroup(securityGroupId);
               throw new RuntimeException(e);
           }
       }

       private String createSecurityGroupForInstance(ResourceModel model) {
           String vpcId;
           try {
               vpcId = getVpcIdFromSubnetId(model.getSubnetId());
           } catch (Throwable e) {
               throw new RuntimeException(e);
           }

           final String securityGroupName = model.getName() + "-" + UUID.randomUUID().toString();

           final CreateSecurityGroupRequest createSecurityGroupRequest = new CreateSecurityGroupRequest()
               .withGroupName(securityGroupName)
               .withDescription("Created for the test WordPress blog: " + model.getName())
               .withVpcId(vpcId);

           final String securityGroupId =
               clientProxy.injectCredentialsAndInvoke(createSecurityGroupRequest, ec2Client::createSecurityGroup)
                          .getGroupId();

           final AuthorizeSecurityGroupIngressRequest authorizeSecurityGroupIngressRequest = new AuthorizeSecurityGroupIngressRequest()
               .withGroupId(securityGroupId)
               .withIpPermissions(openHTTP(), openHTTPS());

           clientProxy.injectCredentialsAndInvoke(authorizeSecurityGroupIngressRequest, ec2Client::authorizeSecurityGroupIngress);

           return securityGroupId;
       }

       private String getVpcIdFromSubnetId(String subnetId) throws Throwable {
           final DescribeSubnetsRequest describeSubnetsRequest = new DescribeSubnetsRequest()
               .withSubnetIds(subnetId);

           final DescribeSubnetsResult describeSubnetsResult =
               clientProxy.injectCredentialsAndInvoke(describeSubnetsRequest, ec2Client::describeSubnets);

           return describeSubnetsResult.getSubnets()
                                       .stream()
                                       .map(Subnet::getVpcId)
                                       .findFirst()
                                       .orElseThrow(() -> {
                                           throw new RuntimeException("Subnet " + subnetId + " not found");
                                       });
       }

       private IpPermission openHTTP() {
           return new IpPermission().withIpProtocol("tcp")
                                    .withFromPort(80)
                                    .withToPort(80)
                                    .withIpv4Ranges(new IpRange().withCidrIp("0.0.0.0/0"));
       }

       private IpPermission openHTTPS() {
           return new IpPermission().withIpProtocol("tcp")
                                    .withFromPort(443)
                                    .withToPort(443)
                                    .withIpv4Ranges(new IpRange().withCidrIp("0.0.0.0/0"));
       }

       private TagSpecification buildTagFromSiteName(String siteName) {
           return new TagSpecification()
               .withResourceType("instance")
               .withTags(new Tag().withKey(SITE_NAME_TAG_KEY).withValue(siteName));
       }

       private Instance updatedInstanceProgress(String instanceId) {
           DescribeInstancesRequest describeInstancesRequest;
           DescribeInstancesResult describeInstancesResult;

           describeInstancesRequest = new DescribeInstancesRequest().withInstanceIds(instanceId);
           describeInstancesResult = clientProxy.injectCredentialsAndInvoke(describeInstancesRequest, ec2Client::describeInstances);
           return describeInstancesResult.getReservations()
                                         .stream()
                                         .map(Reservation::getInstances)
                                         .flatMap(List::stream)
                                         .findFirst()
                                         .orElse(new Instance());
       }

       private void attemptToCleanUpSecurityGroup(String securityGroupId) {
           final DeleteSecurityGroupRequest deleteSecurityGroupRequest = new DeleteSecurityGroupRequest().withGroupId(securityGroupId);
           clientProxy.injectCredentialsAndInvoke(deleteSecurityGroupRequest, ec2Client::deleteSecurityGroup);
       }
   }
   ```

#### Update the Create Handler Unit Test<a name="resource-type-walkthrough-implement-create-handler-unit"></a>

Since our resource type is a high\-level abstraction, a lot of implementation behavior isn't apparent by the name alone\. As such, we'll need to make some additions to our unit tests so that we're not calling the live APIs that are necessary to create the WordPress site\.

1. In your IDE, open the `CreateHandler.java` file, located in the `src/test/java/com/custom/testing/wordpress` folder\.

1. Replace the entire contents of the `CreateHandler.java` file with the following code\.

   ```
   package com.custom.testing.wordpress;

   import software.amazon.cloudformation.proxy.AmazonWebServicesClientProxy;
   import software.amazon.cloudformation.proxy.Logger;
   import software.amazon.cloudformation.proxy.OperationStatus;
   import software.amazon.cloudformation.proxy.ProgressEvent;
   import software.amazon.cloudformation.proxy.ResourceHandlerRequest;
   import com.amazonaws.services.ec2.model.AuthorizeSecurityGroupIngressRequest;
   import com.amazonaws.services.ec2.model.AuthorizeSecurityGroupIngressResult;
   import com.amazonaws.services.ec2.model.CreateSecurityGroupRequest;
   import com.amazonaws.services.ec2.model.CreateSecurityGroupResult;
   import com.amazonaws.services.ec2.model.DescribeInstancesRequest;
   import com.amazonaws.services.ec2.model.DescribeInstancesResult;
   import com.amazonaws.services.ec2.model.DescribeSubnetsRequest;
   import com.amazonaws.services.ec2.model.DescribeSubnetsResult;
   import com.amazonaws.services.ec2.model.GroupIdentifier;
   import com.amazonaws.services.ec2.model.Instance;
   import com.amazonaws.services.ec2.model.InstanceState;
   import com.amazonaws.services.ec2.model.Reservation;
   import com.amazonaws.services.ec2.model.RunInstancesRequest;
   import com.amazonaws.services.ec2.model.RunInstancesResult;
   import com.amazonaws.services.ec2.model.Subnet;

   import org.junit.jupiter.api.BeforeEach;
   import org.junit.jupiter.api.Test;
   import org.junit.jupiter.api.extension.ExtendWith;
   import org.mockito.Mock;
   import org.mockito.junit.jupiter.MockitoExtension;


   import static org.assertj.core.api.Assertions.assertThat;
   import static org.mockito.ArgumentMatchers.any;
   import static org.mockito.Mockito.doReturn;
   import static org.mockito.Mockito.mock;

   @ExtendWith(MockitoExtension.class)
   public class CreateHandlerTest {
       private static String EXPECTED_TIMEOUT_MESSAGE = "Timed out waiting for instance to become available.";

       @Mock
       private AmazonWebServicesClientProxy proxy;

       @Mock
       private Logger logger;

       @BeforeEach
       public void setup() {
           proxy = mock(AmazonWebServicesClientProxy.class);
           logger = mock(Logger.class);
       }

       @Test
       public void testSuccessState() {
           final InstanceState inProgressState = new InstanceState().withName("running");
           final GroupIdentifier group = new GroupIdentifier().withGroupId("sg-1234");
           final Instance instance = new Instance().withInstanceId("i-1234").withState(inProgressState).withPublicIpAddress("54.0.0.0").withSecurityGroups(group);

           final CreateHandler handler = new CreateHandler();

           final ResourceModel model = ResourceModel.builder()
                                                    .name("MyWordPressSite")
                                                    .subnetId("subnet-1234")
                                                    .build();

           final ResourceModel desiredOutputModel = ResourceModel.builder()
                                                                 .instanceId("i-1234")
                                                                 .publicIp("54.0.0.0")
                                                                 .name("MyWordPressSite")
                                                                 .subnetId("subnet-1234")
                                                                 .build();

           final ResourceHandlerRequest<ResourceModel> request = ResourceHandlerRequest.<ResourceModel>builder()
               .desiredResourceState(model)
               .build();

           final CallbackContext context = CallbackContext.builder()
                                                          .stabilizationRetriesRemaining(1)
                                                          .instance(instance)
                                                          .build();

           final ProgressEvent<ResourceModel, CallbackContext> response
               = handler.handleRequest(proxy, request, context, logger);

           assertThat(response).isNotNull();
           assertThat(response.getStatus()).isEqualTo(OperationStatus.SUCCESS);
           assertThat(response.getCallbackContext()).isNull();
           assertThat(response.getCallbackDelaySeconds()).isEqualTo(0);
           assertThat(response.getResourceModel()).isEqualTo(desiredOutputModel);
           assertThat(response.getResourceModels()).isNull();
           assertThat(response.getMessage()).isNull();
           assertThat(response.getErrorCode()).isNull();
       }

       @Test
       public void testInProgressStateInstanceCreationNotInvoked() {
           final InstanceState inProgressState = new InstanceState().withName("in-progress");
           final GroupIdentifier group = new GroupIdentifier().withGroupId("sg-1234");
           final Instance instance = new Instance().withState(inProgressState).withPublicIpAddress("54.0.0.0").withSecurityGroups(group);
           doReturn(new DescribeSubnetsResult().withSubnets(new Subnet().withVpcId("vpc-1234"))).when(proxy).injectCredentialsAndInvoke(any(DescribeSubnetsRequest.class), any());
           doReturn(new RunInstancesResult().withReservation(new Reservation().withInstances(instance))).when(proxy).injectCredentialsAndInvoke(any(RunInstancesRequest.class), any());
           doReturn(new CreateSecurityGroupResult().withGroupId("sg-1234")).when(proxy).injectCredentialsAndInvoke(any(CreateSecurityGroupRequest.class), any());
           doReturn(new AuthorizeSecurityGroupIngressResult()).when(proxy).injectCredentialsAndInvoke(any(AuthorizeSecurityGroupIngressRequest.class), any());

           final CreateHandler handler = new CreateHandler();

           final ResourceModel model = ResourceModel.builder().name("MyWordPressSite").subnetId("subnet-1234").build();

           final ResourceHandlerRequest<ResourceModel> request = ResourceHandlerRequest.<ResourceModel>builder()
               .desiredResourceState(model)
               .build();

           final ProgressEvent<ResourceModel, CallbackContext> response
               = handler.handleRequest(proxy, request, null, logger);

           final CallbackContext desiredOutputContext = CallbackContext.builder()
                                                                       .stabilizationRetriesRemaining(60)
                                                                       .instance(instance)
                                                                       .build();
           assertThat(response).isNotNull();
           assertThat(response.getStatus()).isEqualTo(OperationStatus.IN_PROGRESS);
           assertThat(response.getCallbackContext()).isEqualToComparingFieldByField(desiredOutputContext);
           assertThat(response.getCallbackDelaySeconds()).isEqualTo(0);
           assertThat(response.getResourceModel()).isEqualTo(request.getDesiredResourceState());
           assertThat(response.getResourceModels()).isNull();
           assertThat(response.getMessage()).isNull();
           assertThat(response.getErrorCode()).isNull();
       }

       @Test
       public void testInProgressStateInstanceCreationInvoked() {
           final InstanceState inProgressState = new InstanceState().withName("in-progress");
           final GroupIdentifier group = new GroupIdentifier().withGroupId("sg-1234");
           final Instance instance = new Instance().withState(inProgressState).withPublicIpAddress("54.0.0.0").withSecurityGroups(group);
           final DescribeInstancesResult describeInstancesResult =
               new DescribeInstancesResult().withReservations(new Reservation().withInstances(instance));

           doReturn(describeInstancesResult).when(proxy).injectCredentialsAndInvoke(any(DescribeInstancesRequest.class), any());

           final CreateHandler handler = new CreateHandler();

           final ResourceModel model = ResourceModel.builder().name("MyWordPressSite").subnetId("subnet-1234").build();

           final ResourceHandlerRequest<ResourceModel> request = ResourceHandlerRequest.<ResourceModel>builder()
               .desiredResourceState(model)
               .build();

           final CallbackContext context = CallbackContext.builder()
                                                          .stabilizationRetriesRemaining(60)
                                                          .instance(instance)
                                                          .build();

           final ProgressEvent<ResourceModel, CallbackContext> response
               = handler.handleRequest(proxy, request, context, logger);

           final CallbackContext desiredOutputContext = CallbackContext.builder()
                                                                       .stabilizationRetriesRemaining(59)
                                                                       .instance(instance)
                                                                       .build();

           assertThat(response).isNotNull();
           assertThat(response.getStatus()).isEqualTo(OperationStatus.IN_PROGRESS);
           assertThat(response.getCallbackContext()).isEqualToComparingFieldByField(desiredOutputContext);
           assertThat(response.getCallbackDelaySeconds()).isEqualTo(0);
           assertThat(response.getResourceModel()).isEqualTo(request.getDesiredResourceState());
           assertThat(response.getResourceModels()).isNull();
           assertThat(response.getMessage()).isNull();
           assertThat(response.getErrorCode()).isNull();
       }

       @Test
       public void testStabilizationTimeout() {
           final CreateHandler handler = new CreateHandler();

           final ResourceModel model = ResourceModel.builder().name("MyWordPressSite").subnetId("subnet-1234").build();

           final ResourceHandlerRequest<ResourceModel> request = ResourceHandlerRequest.<ResourceModel>builder()
               .desiredResourceState(model)
               .build();

           final CallbackContext context = CallbackContext.builder()
                                                          .stabilizationRetriesRemaining(0)
                                                          .instance(new Instance().withState(new InstanceState().withName("in-progress")))
                                                          .build();

           try {
               handler.handleRequest(proxy, request, context, logger);
           } catch (RuntimeException e) {
               assertThat(e.getMessage()).isEqualTo(EXPECTED_TIMEOUT_MESSAGE);
           }
       }
   }
   ```

### Implement the Delete Handler<a name="resource-type-walkthrough-implement-delete-handler"></a>

We'll also need to implement a delete handler\. At a high level, the delete handler needs to accomplish the following:

1. Find the security groups attached to the EC2 instance that is hosting the WordPress page\.

1. Delete the instance\.

1. Delete the security groups\.

Again, we'll implement the delete handler as a state machine\.

#### Code the Delete Handler<a name="resource-type-walkthrough-implement-delete-handler-code"></a>

1. In your IDE, open the `DeleteHandler.java` file, located in the `src/main/java/com/custom/testing/wordpress` folder\.

1. Replace the entire contents of the `DeleteHandler.java` file with the following code\.

   ```
   package com.custom.testing.wordpress;

   import software.amazon.cloudformation.proxy.AmazonWebServicesClientProxy;
   import software.amazon.cloudformation.proxy.HandlerErrorCode;
   import software.amazon.cloudformation.proxy.Logger;
   import software.amazon.cloudformation.proxy.OperationStatus;
   import software.amazon.cloudformation.proxy.ProgressEvent;
   import software.amazon.cloudformation.proxy.ResourceHandlerRequest;
   import com.amazonaws.services.ec2.AmazonEC2;
   import com.amazonaws.services.ec2.AmazonEC2ClientBuilder;
   import com.amazonaws.services.ec2.model.DeleteSecurityGroupRequest;
   import com.amazonaws.services.ec2.model.DescribeInstancesRequest;
   import com.amazonaws.services.ec2.model.DescribeInstancesResult;
   import com.amazonaws.services.ec2.model.GroupIdentifier;
   import com.amazonaws.services.ec2.model.Instance;
   import com.amazonaws.services.ec2.model.Reservation;
   import com.amazonaws.services.ec2.model.TerminateInstancesRequest;

   import java.util.List;
   import java.util.stream.Collectors;

   public class DeleteHandler extends BaseHandler<CallbackContext> {
       private static final String SUPPORTED_REGION = "us-west-2";
       private static final String DELETED_INSTANCE_STATE = "terminated";
       private static final int NUMBER_OF_STATE_POLL_RETRIES = 60;
       private static final int POLL_RETRY_DELAY_IN_MS = 5000;
       private static final String TIMED_OUT_MESSAGE = "Timed out waiting for instance to terminate.";

       private AmazonWebServicesClientProxy clientProxy;
       private AmazonEC2 ec2Client;

       @Override
       public ProgressEvent<ResourceModel, CallbackContext> handleRequest (
           final AmazonWebServicesClientProxy proxy,
           final ResourceHandlerRequest<ResourceModel> request,
           final CallbackContext callbackContext,
           final Logger logger) {

           final ResourceModel model = request.getDesiredResourceState();

           clientProxy = proxy;
           ec2Client = AmazonEC2ClientBuilder.standard().withRegion(SUPPORTED_REGION).build();
           final CallbackContext currentContext = callbackContext == null ?
                                                  CallbackContext.builder().stabilizationRetriesRemaining(NUMBER_OF_STATE_POLL_RETRIES).build() :
                                                  callbackContext;

           // This Lambda will continually be re-invoked with the current state of the instance, finally succeeding when state stabilizes.
           return deleteInstanceAndUpdateProgress(model, currentContext);
       }

       private ProgressEvent<ResourceModel, CallbackContext> deleteInstanceAndUpdateProgress(ResourceModel model, CallbackContext callbackContext) {

           if (callbackContext.getStabilizationRetriesRemaining() == 0) {
               throw new RuntimeException(TIMED_OUT_MESSAGE);
           }

           if (callbackContext.getInstanceSecurityGroups() == null) {
               final Instance currentInstanceState = currentInstanceState(model.getInstanceId());

               if (DELETED_INSTANCE_STATE.equals(currentInstanceState.getState().getName())) {
                   return ProgressEvent.<ResourceModel, CallbackContext>builder()
                       .status(OperationStatus.FAILED)
                       .errorCode(HandlerErrorCode.NotFound)
                       .build();
               }

               final List<String> instanceSecurityGroups = currentInstanceState
                   .getSecurityGroups()
                   .stream()
                   .map(GroupIdentifier::getGroupId)
                   .collect(Collectors.toList());

               return ProgressEvent.<ResourceModel, CallbackContext>builder()
                   .resourceModel(model)
                   .status(OperationStatus.IN_PROGRESS)
                   .callbackContext(CallbackContext.builder()
                                                   .stabilizationRetriesRemaining(NUMBER_OF_STATE_POLL_RETRIES)
                                                   .instanceSecurityGroups(instanceSecurityGroups)
                                                   .build())
                   .build();
           }

           if (callbackContext.getInstance() == null) {
               return ProgressEvent.<ResourceModel, CallbackContext>builder()
                   .resourceModel(model)
                   .status(OperationStatus.IN_PROGRESS)
                   .callbackContext(CallbackContext.builder()
                                                   .instance(deleteInstance(model.getInstanceId()))
                                                   .instanceSecurityGroups(callbackContext.getInstanceSecurityGroups())
                                                   .stabilizationRetriesRemaining(NUMBER_OF_STATE_POLL_RETRIES)
                                                   .build())
                   .build();
           } else if (callbackContext.getInstance().getState().getName().equals(DELETED_INSTANCE_STATE)) {
               callbackContext.getInstanceSecurityGroups().forEach(this::deleteSecurityGroup);
               return ProgressEvent.<ResourceModel, CallbackContext>builder()
                   .resourceModel(model)
                   .status(OperationStatus.SUCCESS)
                   .build();
           } else {
               try {
                   Thread.sleep(POLL_RETRY_DELAY_IN_MS);
               } catch (InterruptedException e) {
                   throw new RuntimeException(e);
               }
               return ProgressEvent.<ResourceModel, CallbackContext>builder()
                   .resourceModel(model)
                   .status(OperationStatus.IN_PROGRESS)
                   .callbackContext(CallbackContext.builder()
                                                   .instance(currentInstanceState(model.getInstanceId()))
                                                   .instanceSecurityGroups(callbackContext.getInstanceSecurityGroups())
                                                   .stabilizationRetriesRemaining(callbackContext.getStabilizationRetriesRemaining() - 1)
                                                   .build())
                   .build();
           }

       }

       private Instance deleteInstance(String instanceId) {
           final TerminateInstancesRequest terminateInstancesRequest = new TerminateInstancesRequest().withInstanceIds(instanceId);
           return clientProxy.injectCredentialsAndInvoke(terminateInstancesRequest, ec2Client::terminateInstances)
                             .getTerminatingInstances()
                             .stream()
                             .map(instance -> new Instance().withState(instance.getCurrentState()).withInstanceId(instance.getInstanceId()))
                             .findFirst()
                             .orElse(new Instance());
       }

       private Instance currentInstanceState(String instanceId) {
           DescribeInstancesRequest describeInstancesRequest;
           DescribeInstancesResult describeInstancesResult;

           describeInstancesRequest = new DescribeInstancesRequest().withInstanceIds(instanceId);
           describeInstancesResult = clientProxy.injectCredentialsAndInvoke(describeInstancesRequest, ec2Client::describeInstances);
           return describeInstancesResult.getReservations()
                                         .stream()
                                         .map(Reservation::getInstances)
                                         .flatMap(List::stream)
                                         .findFirst()
                                         .orElse(new Instance());
       }

       private void deleteSecurityGroup(String securityGroupId) {
           final DeleteSecurityGroupRequest deleteSecurityGroupRequest = new DeleteSecurityGroupRequest().withGroupId(securityGroupId);
           clientProxy.injectCredentialsAndInvoke(deleteSecurityGroupRequest, ec2Client::deleteSecurityGroup);
       }
   }
   ```

#### Update the Delete Handler Unit Test<a name="resource-type-walkthrough-implement-delete-handler-unit"></a>

We'll also need to update the unit test for the delete handler\.

1. In your IDE, open the `DeleteHandler.java` file, located in the `src/test/java/com/custom/testing/wordpress` folder\.

1. Replace the entire contents of the `DeleteHandler.java` file with the following code\.

   ```
   package com.custom.testing.wordpress;

   import software.amazon.cloudformation.proxy.AmazonWebServicesClientProxy;
   import software.amazon.cloudformation.proxy.HandlerErrorCode;
   import software.amazon.cloudformation.proxy.Logger;
   import software.amazon.cloudformation.proxy.OperationStatus;
   import software.amazon.cloudformation.proxy.ProgressEvent;
   import software.amazon.cloudformation.proxy.ResourceHandlerRequest;
   import com.amazonaws.services.ec2.model.DeleteSecurityGroupRequest;
   import com.amazonaws.services.ec2.model.DeleteSecurityGroupResult;
   import com.amazonaws.services.ec2.model.DescribeInstancesRequest;
   import com.amazonaws.services.ec2.model.DescribeInstancesResult;
   import com.amazonaws.services.ec2.model.GroupIdentifier;
   import com.amazonaws.services.ec2.model.Instance;
   import com.amazonaws.services.ec2.model.InstanceState;
   import com.amazonaws.services.ec2.model.InstanceStateChange;
   import com.amazonaws.services.ec2.model.Reservation;
   import com.amazonaws.services.ec2.model.TerminateInstancesRequest;
   import com.amazonaws.services.ec2.model.TerminateInstancesResult;

   import org.junit.jupiter.api.BeforeEach;
   import org.junit.jupiter.api.Test;
   import org.junit.jupiter.api.extension.ExtendWith;
   import org.mockito.Mock;
   import org.mockito.junit.jupiter.MockitoExtension;

   import java.util.Arrays;


   import static org.assertj.core.api.Assertions.assertThat;
   import static org.mockito.ArgumentMatchers.any;
   import static org.mockito.Mockito.doReturn;
   import static org.mockito.Mockito.mock;

   @ExtendWith(MockitoExtension.class)
   public class DeleteHandlerTest {
       private static String EXPECTED_TIMEOUT_MESSAGE = "Timed out waiting for instance to terminate.";

       @Mock
       private AmazonWebServicesClientProxy proxy;

       @Mock
       private Logger logger;

       @BeforeEach
       public void setup() {
           proxy = mock(AmazonWebServicesClientProxy.class);
           logger = mock(Logger.class);
       }

       @Test
       public void testSuccessState() {
           final DeleteSecurityGroupResult deleteSecurityGroupResult = new DeleteSecurityGroupResult();
           doReturn(deleteSecurityGroupResult).when(proxy).injectCredentialsAndInvoke(any(DeleteSecurityGroupRequest.class), any());

           final DeleteHandler handler = new DeleteHandler();

           final ResourceModel model = ResourceModel.builder().instanceId("i-1234").build();

           final ResourceHandlerRequest<ResourceModel> request = ResourceHandlerRequest.<ResourceModel>builder()
               .desiredResourceState(model)
               .build();

           final CallbackContext context = CallbackContext.builder()
                                                          .stabilizationRetriesRemaining(1)
                                                          .instanceSecurityGroups(Arrays.asList("sg-1234"))
                                                          .instance(new Instance().withState(new InstanceState().withName("terminated")))
                                                          .build();

           final ProgressEvent<ResourceModel, CallbackContext> response
               = handler.handleRequest(proxy, request, context, logger);

           assertThat(response).isNotNull();
           assertThat(response.getStatus()).isEqualTo(OperationStatus.SUCCESS);
           assertThat(response.getCallbackContext()).isNull();
           assertThat(response.getCallbackDelaySeconds()).isEqualTo(0);
           assertThat(response.getResourceModel()).isEqualTo(request.getDesiredResourceState());
           assertThat(response.getResourceModels()).isNull();
           assertThat(response.getMessage()).isNull();
           assertThat(response.getErrorCode()).isNull();
       }

       @Test
       public void testHandlerInvokedWhenInstanceIsAlreadyTerminated() {
           final DescribeInstancesResult describeInstancesResult =
               new DescribeInstancesResult().withReservations(new Reservation().withInstances(new Instance().withState(new InstanceState().withName("terminated"))
                                                                                                            .withSecurityGroups(new GroupIdentifier().withGroupId("sg-1234"))));
           doReturn(describeInstancesResult).when(proxy).injectCredentialsAndInvoke(any(DescribeInstancesRequest.class), any());

           final DeleteHandler handler = new DeleteHandler();

           final ResourceModel model = ResourceModel.builder().instanceId("i-1234").build();

           final ResourceHandlerRequest<ResourceModel> request = ResourceHandlerRequest.<ResourceModel>builder()
               .desiredResourceState(model)
               .build();

           final ProgressEvent<ResourceModel, CallbackContext> response
               = handler.handleRequest(proxy, request, null, logger);

           assertThat(response).isNotNull();
           assertThat(response.getStatus()).isEqualTo(OperationStatus.FAILED);
           assertThat(response.getCallbackContext()).isNull();
           assertThat(response.getCallbackDelaySeconds()).isEqualTo(0);
           assertThat(response.getResourceModel()).isNull();
           assertThat(response.getResourceModels()).isNull();
           assertThat(response.getMessage()).isNull();
           assertThat(response.getErrorCode()).isEqualTo(HandlerErrorCode.NotFound);
       }

       @Test
       public void testInProgressStateSecurityGroupsNotGathered() {
           final DescribeInstancesResult describeInstancesResult =
               new DescribeInstancesResult().withReservations(new Reservation().withInstances(new Instance().withState(new InstanceState().withName("running"))
                                                                                                            .withSecurityGroups(new GroupIdentifier().withGroupId("sg-1234"))));
           doReturn(describeInstancesResult).when(proxy).injectCredentialsAndInvoke(any(DescribeInstancesRequest.class), any());

           final DeleteHandler handler = new DeleteHandler();

           final ResourceModel model = ResourceModel.builder().instanceId("i-1234").build();

           final ResourceHandlerRequest<ResourceModel> request = ResourceHandlerRequest.<ResourceModel>builder()
               .desiredResourceState(model)
               .build();

           final ProgressEvent<ResourceModel, CallbackContext> response
               = handler.handleRequest(proxy, request, null, logger);

           final CallbackContext desiredOutputContext = CallbackContext.builder()
                                                                       .stabilizationRetriesRemaining(60)
                                                                       .instanceSecurityGroups(Arrays.asList("sg-1234"))
                                                                       .build();
           assertThat(response).isNotNull();
           assertThat(response.getStatus()).isEqualTo(OperationStatus.IN_PROGRESS);
           assertThat(response.getCallbackContext()).isEqualToComparingFieldByField(desiredOutputContext);
           assertThat(response.getCallbackDelaySeconds()).isEqualTo(0);
           assertThat(response.getResourceModel()).isEqualTo(request.getDesiredResourceState());
           assertThat(response.getResourceModels()).isNull();
           assertThat(response.getMessage()).isNull();
           assertThat(response.getErrorCode()).isNull();
       }

       @Test
       public void testInProgressStateSecurityGroupsGathered() {
           final InstanceState inProgressState = new InstanceState().withName("in-progress");
           final TerminateInstancesResult terminateInstancesResult =
               new TerminateInstancesResult().withTerminatingInstances(new InstanceStateChange().withCurrentState(inProgressState));
           doReturn(terminateInstancesResult).when(proxy).injectCredentialsAndInvoke(any(TerminateInstancesRequest.class), any());

           final DeleteHandler handler = new DeleteHandler();

           final ResourceModel model = ResourceModel.builder().instanceId("i-1234").build();

           final ResourceHandlerRequest<ResourceModel> request = ResourceHandlerRequest.<ResourceModel>builder()
               .desiredResourceState(model)
               .build();

           final CallbackContext context = CallbackContext.builder()
                                                          .stabilizationRetriesRemaining(60)
                                                          .instanceSecurityGroups(Arrays.asList("sg-1234"))
                                                          .build();

           final ProgressEvent<ResourceModel, CallbackContext> response
               = handler.handleRequest(proxy, request, context, logger);

           final CallbackContext desiredOutputContext = CallbackContext.builder()
                                                                       .stabilizationRetriesRemaining(60)
                                                                       .instanceSecurityGroups(context.getInstanceSecurityGroups())
                                                                       .instance(new Instance().withState(inProgressState))
                                                                       .build();

           assertThat(response).isNotNull();
           assertThat(response.getStatus()).isEqualTo(OperationStatus.IN_PROGRESS);
           assertThat(response.getCallbackContext()).isEqualToComparingFieldByField(desiredOutputContext);
           assertThat(response.getCallbackDelaySeconds()).isEqualTo(0);
           assertThat(response.getResourceModel()).isEqualTo(request.getDesiredResourceState());
           assertThat(response.getResourceModels()).isNull();
           assertThat(response.getMessage()).isNull();
           assertThat(response.getErrorCode()).isNull();
       }

       @Test
       public void testInProgressStateInstanceTerminationInvoked() {
           final InstanceState inProgressState = new InstanceState().withName("in-progress");
           final GroupIdentifier group = new GroupIdentifier().withGroupId("sg-1234");
           final Instance instance = new Instance().withState(inProgressState).withSecurityGroups(group);
           final DescribeInstancesResult describeInstancesResult =
               new DescribeInstancesResult().withReservations(new Reservation().withInstances(instance));
           doReturn(describeInstancesResult).when(proxy).injectCredentialsAndInvoke(any(DescribeInstancesRequest.class), any());

           final DeleteHandler handler = new DeleteHandler();

           final ResourceModel model = ResourceModel.builder().instanceId("i-1234").build();

           final ResourceHandlerRequest<ResourceModel> request = ResourceHandlerRequest.<ResourceModel>builder()
               .desiredResourceState(model)
               .build();

           final CallbackContext context = CallbackContext.builder()
                                                          .stabilizationRetriesRemaining(60)
                                                          .instance(new Instance().withState(inProgressState).withSecurityGroups(group))
                                                          .instanceSecurityGroups(Arrays.asList("sg-1234"))
                                                          .build();

           final ProgressEvent<ResourceModel, CallbackContext> response
               = handler.handleRequest(proxy, request, context, logger);

           final CallbackContext desiredOutputContext = CallbackContext.builder()
                                                                       .stabilizationRetriesRemaining(59)
                                                                       .instanceSecurityGroups(context.getInstanceSecurityGroups())
                                                                       .instance(new Instance().withState(inProgressState).withSecurityGroups(group))
                                                                       .build();

           assertThat(response).isNotNull();
           assertThat(response.getStatus()).isEqualTo(OperationStatus.IN_PROGRESS);
           assertThat(response.getCallbackContext()).isEqualToComparingFieldByField(desiredOutputContext);
           assertThat(response.getCallbackDelaySeconds()).isEqualTo(0);
           assertThat(response.getResourceModel()).isEqualTo(request.getDesiredResourceState());
           assertThat(response.getResourceModels()).isNull();
           assertThat(response.getMessage()).isNull();
           assertThat(response.getErrorCode()).isNull();
       }

       @Test
       public void testStabilizationTimeout() {
           final DeleteHandler handler = new DeleteHandler();

           final ResourceModel model = ResourceModel.builder().instanceId("i-1234").build();

           final ResourceHandlerRequest<ResourceModel> request = ResourceHandlerRequest.<ResourceModel>builder()
               .desiredResourceState(model)
               .build();

           final CallbackContext context = CallbackContext.builder()
                                                          .stabilizationRetriesRemaining(0)
                                                          .instanceSecurityGroups(Arrays.asList("sg-1234"))
                                                          .instance(new Instance().withState(new InstanceState().withName("terminated")))
                                                          .build();

           try {
               handler.handleRequest(proxy, request, context, logger);
           } catch (RuntimeException e) {
               assertThat(e.getMessage()).isEqualTo(EXPECTED_TIMEOUT_MESSAGE);
           }
       }
   }
   ```

## Test the Resource Provider<a name="resource-type-walkthrough-test"></a>

Next, we'll use the AWS SAM CLI to test locally that our resource will work as expected once we submit it to the CloudFormation registry\. To do this, we'll need to define tests for the SAM to run against our create and delete handlers\.

### Create the SAM Test Files<a name="resource-type-walkthrough-test-files"></a>

1. Create two files:
   + `package-root/sam-tests/create.json`
   + `package-root/sam-tests/delete.json`

   Where *package\-root* is the root of the resource project\. For our walkthrough example, the files would be:
   + `custom-testing-wordpress/sam-tests/create.json`
   + `custom-testing-wordpress/sam-tests/delete.json`

1. In `custom-testing-wordpress/sam-tests/create.json`, paste the following test\.
**Note**
Add the necessary information, such as credentials and log group name, and remove any comments in the file before testing\.
To generate temporary credentials, you can use `aws sts get-session-token`\.

   ```
   {
       "credentials": {
           # Real STS credentials need to go here.
           "accessKeyId": "",
           "secretAccessKey": "",
           "sessionToken": ""
       },
       "action": "CREATE",
       "request": {
           "clientRequestToken": "4b90a7e4-b790-456b-a937-0cfdfa211dfe", # Can be any UUID.
           "desiredResourceState": {
               "Name": "MyBlog",
               "SubnetId": "subnet-0bc6136e" # This should be a real subnet that exists in the account you're testing against.
           },
           "logicalResourceIdentifier": "MyResource"
       },
       "callbackContext": null
   }
   ```

1. In `custom-testing-wordpress/sam-tests/delete.json`, paste the following test\.
**Note**
Add the necessary information, such as credentials and log group name, and remove any comments in the file before testing\.
To generate temporary credentials, you can use `aws sts get-session-token`\.

   ```
   {
       "credentials": {
           # Real STS credentials need to go here.
           "accessKeyId": "",
           "secretAccessKey": "",
           "sessionToken": ""
       },
       "action": "DELETE",
       "request": {
           "clientRequestToken": "4b90a7e4-b790-456b-a937-0cfdfa211dfe",  # Can be any UUID.
           "desiredResourceState": {
               "Name": "MyBlog",
               "InstanceId": "i-0167b19dd4c1efbf3", # This should be the instance ID that was created in the "create.json" test.
               "SubnetId": "subnet-0bc6136e" # This should be a real subnet that exists in the account you're testing against.
           },
           "logicalResourceIdentifier": "MyResource"
       },
       "callbackContext": null
   }
   ```

### Test the Create Handler<a name="resource-type-walkthrough-test-create"></a>

Once you've created the `custom-testing-wordpress/sam-tests/create.json` test file, you can use it to test your create handler\.

Ensure Docker is running on your computer\.

1. Invoke the SAM function from the resource package root directory using the following commands\.

   ```
   sam local invoke TestEntrypoint --event sam-tests/create.json
   ```
**Note**
Occasionally these tests will fail with a retry\-able error\. In such a case, run the tests again to determine whether the issue was transient\.

   Because the create handler was written as a state machine, invoking the tests will return an output that represents a state\. For example:

   ```
   {
       "callbackDelaySeconds": 0,
       "resourceModel": {
           "SubnetId": "subnet-0bc6136e",
           "Name": "MyBlog"
       },
       "callbackContext": {
           "instance": {
               "subnetId": "subnet-0bc6136e",
               "virtualizationType": "hvm",
               "capacityReservationSpecification": {
                   "capacityReservationPreference": "open"
               },
               "amiLaunchIndex": 0,
               "elasticInferenceAcceleratorAssociations": [],
               "sourceDestCheck": true,
               "stateReason": {
                   "code": "pending",
                   "message": "pending"
               },
               "instanceId": "i-0b6978477c0e9d358",
               "vpcId": "vpc-eb80788e",
               "hypervisor": "xen",
               "rootDeviceName": "/dev/sda1",
               "productCodes": [],
               "state": {
                   "code": 0,
                   "name": "pending"
               },
               "architecture": "x86_64",
               "ebsOptimized": false,
               "imageId": "ami-04fb0368671b6f138",
               "blockDeviceMappings": [],
               "stateTransitionReason": "",
               "clientToken": "207dc686-e95c-4df9-8fcb-ee22bbdde963",
               "instanceType": "m4.large",
               "cpuOptions": {
                   "threadsPerCore": 2,
                   "coreCount": 1
               },
               "monitoring": {
                   "state": "disabled"
               },
               "publicDnsName": "",
               "privateIpAddress": "172.0.0.133",
               "rootDeviceType": "ebs",
               "tags": [
                   {
                       "value": "MyBlog",
                       "key": "Name"
                   }
               ],
               "launchTime": 1567718644000,
               "elasticGpuAssociations": [],
               "licenses": [],
               "networkInterfaces": [
                   {
                       "networkInterfaceId": "eni-0e450b35a159b60fe",
                       "privateIpAddresses": [
                           {
                               "privateIpAddress": "172.0.0.133",
                               "primary": true
                           }
                       ],
                       "subnetId": "subnet-0bc6136e",
                       "description": "",
                       "groups": [
                           {
                               "groupName": "MyBlog-cbb70fca-4704-430b-b67b-7d6d550e0592",
                               "groupId": "sg-063679dc7681610c3"
                           }
                       ],
                       "ipv6Addresses": [],
                       "ownerId": "671472782477",
                       "sourceDestCheck": true,
                       "privateIpAddress": "172.0.0.133",
                       "interfaceType": "interface",
                       "macAddress": "02:e1:4b:d1:f7:40",
                       "attachment": {
                           "attachmentId": "eni-attach-0a01c63e4b45c4a5d",
                           "deleteOnTermination": true,
                           "deviceIndex": 0,
                           "attachTime": 1567718644000,
                           "status": "attaching"
                       },
                       "vpcId": "vpc-eb80788e",
                       "status": "in-use"
                   }
               ],
               "privateDnsName": "ip-172-0-0-133.us-west-2.compute.internal",
               "securityGroups": [
                   {
                       "groupName": "MyBlog-cbb70fca-4704-430b-b67b-7d6d550e0592",
                       "groupId": "sg-063679dc7681610c3"
                   }
               ],
               "placement": {
                   "groupName": "",
                   "tenancy": "default",
                   "availabilityZone": "us-west-2b"
               }
           },
           "stabilizationRetriesRemaining": 60
       },
       "status": "IN_PROGRESS"
   }
   ```

1. From the test response, copy the contents of the `callbackContext`, and paste it into the `callbackContext` section of the `custom-testing-wordpress/sam-tests/create.json` file\.

1. Invoke the `TestEntrypoint` function again\.

   ```
   sam local invoke TestEntrypoint --event sam-tests/create.json
   ```

   If the resource has yet to complete provisioning, the test returns a response with a `status` of `IN_PROGRESS`\. Once the resource has completed provisioning, the test returns a response with a `status` of `SUCCESS`\. For example:

   ```
   {
       "callbackDelaySeconds": 0,
       "resourceModel": {
           "InstanceId": "i-0b6978477c0e9d358",
           "PublicIp": "34.211.69.121",
           "SubnetId": "subnet-0bc6136e",
           "Name": "MyBlog"
       },
       "status": "SUCCESS"
   }
   ```

1. Repeat the previous two steps until the resource has completed\.

When the resource completes provisioning, the test response contains both its `PublicIp` and `InstanceId`:
+ You can use the `PublicIp` value to navigate to the WordPress site\.
+ You can use the `InstanceId` value to test the delete handler, as described below\.

### Test the Delete Handler<a name="resource-type-walkthrough-test-delete"></a>

Once you've created the `custom-testing-wordpress/sam-tests/delete.json` test file, you can use it to test your delete handler\.

Ensure Docker is running on your computer\.

1. Invoke the `TestEntrypoint` function from the resource package root directory using the following commands\.

   ```
   sam local invoke TestEntrypoint --event sam-tests/delete.json
   ```
**Note**
Occasionally these tests will fail with a retry\-able error\. In such a case, run the tests again to determine whether the issue was transient\.

   As with the create handler, the delete handler was written as a state machine, so invoking the test will return an output that represents a state\.

1. From the test response, copy the contents of the `callbackContext`, and paste it into the `callbackContext` section of the `custom-testing-wordpress/sam-tests/delete.json` file\.

1. Invoke the `TestEntrypoint` function again\.

   ```
   sam local invoke TestEntrypoint --event sam-tests/delete.json
   ```

   If the resource has yet to complete provisioning, the test returns a response with a `status` of `IN_PROGRESS`\. Once the resource has completed provisioning, the test returns a response with a `status` of `SUCCESS`\.

1. Repeat the previous two steps until the resource has completed\.

### Performing Resource Contract Tests<a name="resource-type-walkthrough-test-contract"></a>

Resource contract tests verify that the resource type provider schema you've defined properly catches property values that will fail when passed to the underlying APIs called from within your resource handlers\. This provides a way of validating user input before passing it to the resource handlers\. For example, in the `Custom::Testing::WordPress` resource type provide schema \(in the `custom-testing-wordpress.json` file\), we specified regex patterns for the `Name` and `SubnetId` properties, and set the maximum length of `Name` as 219 characters\. Contract tests are intended to stress and validate those input definitions\.

#### Specify Resource Contract Test Override Values<a name="resource-type-walkthrough-test-contract-override"></a>

The CloudFormation CLI performs resource contract tests using input that is generated from the patterns you define in your resource's property definitions\. However, some inputs can't be randomly generated\. For example, the `Custom::Testing::WordPress` resource requires an actual subnet ID for testing, not just a string that matches the appearance of a subnet ID\. So in order to test this property, we need to include a file with actual values for the resource contract tests to use\. an overrides\.json at the root of our project that looks like this:

1. Navigate to the root of your project\.

1. Create a file named `overrides.json`\.

1. Include the following override, specifying an actual subnet ID to use when performing resource contract tests\.

   ```
   {
       "CREATE": {
           "/SubnetId": "subnet-0bc6136e" # This should be a real subnet that exists in the account you're testing against.
       }
   }
   ```

#### Run the Resource Contract Tests<a name="resource-type-walkthrough-test-contract-run"></a>

To run resource contract tests, you'll need two shell sessions\.

1. In a new session, run `sam local start-lambda`\.

1. From the resource package root directory, in a session that is aware of the CloudFormation CLI, run `cfn test`\.

   The session that is running `sam local start-lambda` will display information about the status of your tests\.

## Submit the Resource Provider<a name="resource-type-walkthrough-submit"></a>

Once you have completed implementing and testing your resource provided, the final step is to submit it to the CloudFormation registry\. This makes it available for use in stack operations in the account and region in which it was submitted\.
+ In a terminal, run the `submit` command to register the resource provider in the us\-west\-2 region\.

  ```
  $ cfn submit -v --region us-west-2
  ```

  The CloudFormation CLI validates the included resource provider schema, packages your resource provide project and uploads it to the CloudFormation registry, and then returns a registration token\.

  ```
  Validating your resource specification...
  Packaging Java project
  Creating managed upload infrastructure stack
  Managed upload infrastructure stack was successfully created
  Registration in progress with token: 3c27b9e6-dca4-4892-ba4e-3c0example
  ```

Resource provider registration is an asynchronous operation\. You can use the supplied registration token to track the progress of your provider registration request using the [DescribeTypeRegistration](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeTypeRegistration.html) action of the CloudFormation API\.

**Note**
If you update your resource provider, you can submit a new version of that resource provider\. Every time you submit your resource provider, CloudFormation generates a new version of that resource provider\.
To set the default version of a resource provider, use [SetTypeDefaultVersion](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_SetTypeDefaultVersion.html)\. For example:

```
aws cloudformation set-type-default-version --type "RESOURCE" --type-name "Custom::Testing::WordPress" --version-id "00000002"
```
To retrieve information about the versions of a resource provider, use [ListTypeVersions](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ListTypeVersions.html)\. For example:

```
aws cloudformation list-type-versions --type "RESOURCE" --type-name "Custom::Testing::WordPress"
```

## Provision the Resource in a CloudFormation Stack<a name="resource-type-walkthrough-provision"></a>

Once the registration request for your resource provider has completed successfully, you can create a stack including resources of that type\.

**Note**
Use [DescribeTypeRegistration](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeTypeRegistration.html) to determine when your resource provider is successfully registration registered with a status of `COMPLETE`\. You should also see your new resource provider listed in the [CloudFormation console](https://docs.aws.amazon.com/resource-types.html#resource-types-view)\.

1. Save the following JSON as a stack template, with the name `stack.json`\.

   ```
   {
       "AWSTemplateFormatVersion": "2010-09-09",
       "Description": "WordPress stack",
       "Resources": {
           "MyWordPressSite": {
               "Type": "Custom::Testing::WordPress",
               "Properties": {
                   "SubnetId": "subnet-0bc6136e", ## Note that this should be replaced with a subnet that exists in your account.
                   "Name": "MyWebsite"
               }
           }
       }
   }
   ```

1. Use the template to create a stack\.

   Navigate to the folder in which you saved the `stack.json` file, and create a stack named `wordpress`\.

   ```
   aws cloudformation create-stack --region us-west-2 \
   --template-body "file://stack.json" \
   --stack-name "wordpress"
   ```

   As CloudFormation creates the stack, it should invoke your resource provider create handler to provision a resource of type `Custom::Testing::WordPress` as part of the `wordpress` stack\.

As a final test of the resource provider delete handler, you can delete the `wordpress` stack\.

```
aws cloudformation delete-stack --region us-west-2 \
--stack-name wordpress
```
