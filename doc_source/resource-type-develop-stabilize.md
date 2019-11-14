# Progress Chaining, Stabilization and Callback Pattern<a name="resource-type-develop-stabilize"></a>

Often when you develop CloudFormation resources, when interacting with web service APIs you need to chain them in sequence to apply the desired state\. CloudFormation provides a framework to write these chain patterns\. The framework does a lot of the heavy lifting needed to handle error conditions, throttle when calling downstream API, and more\. The framework provides callbacks that the handler can use to inspect and change the behavior when making these service calls\.

Most web service API calls follows a typical pattern:

1. Initiate the call context for the API\.

1. Transform the incoming resource model properties to the underlying service API request\.

1. Make the service call\.

1. Handle errors\. \(Optional\)

1. Handle stabilization\. \(Optional, if you need resource to be in a specific state before you apply the next state\.\)

1. Finalize progress to the next part of the call chain, or indicate successful completion\.

In writing the handler, you do not need to do anything special with replay/continuation semantics\. The framework ensures that the call chain is effectively resumed from where it was halted\. This is essentially useful when the wait time for resource stabilization runs into minutes or even hours\.

## Sample: Kinesis Stream Integration<a name="resource-type-develop-stabilize-example"></a>

Here is an example integration against AWS service APIs for a Kinesis Stream\. A snippet of the Kinesis resource model is shown below:

```
{
    "typeName": "AWS::Kinesis::Stream",
    "description": "Resource Type definition for AWS::Kinesis::Stream",
    "definitions": {
        ...
    },
    "properties": {
        "Arn": {
            "type": "string"
        },
        "Name": {
            "type": "string",
            "pattern": "[a-zA-Z0-9_.-]+"
        },
        "RetentionPeriodHours": {
            "type": "integer",
            "minimum": 24,
            "maximum": 168
        },
        "ShardCount": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100000
        },
        "StreamEncryption": {
            "$ref": "#/definitions/AWSKinesisStreamStreamEncryption"
        },
        "Tags": {
            "type": "array",
            "uniqueItems": true,
            "items": {
                "$ref": "#/definitions/Tag"
            },
            "maximum": 50
        }
    }
    ...
}
```

And a sample CloudFormation template for creating this resource in a stack:

```
---
AWSTemplateFormatVersion: '2010-09-09'
Description: AWS MetricFilter
Resources:
  KinesisStream:
    Type: AWS::Kinesis::Stream
    Properties:
      ShardCount: 100
      RetentionPeriodHours: 36
      Tags:
      - Key: '1'
        Value: one
      - Key: '2'
        Value: two
      StreamEncryption:
        EncryptionType: KMS
        KeyId: alias/KinesisEncryption
```

For Kinesis, the stream must first be created with a name and shard count, then tags can be applied, followed by encryption\. After creating a stream, but before any other configuration can be applied, the stream must be in an ACTIVE state\.

Here is the example of the using the progress\-chaining and callback pattern to apply state consistently\. Note that much of the error handling is delegated to the framework\. The CloudFormation CLI provides some error handling on interpreting errors that can be retried after a delay\. The framework provides a fluent API that guides the developer with the right set of calls with strong typing and code completion capabilities in IDEs\.

```
public class CreateHandler extends BaseKinesisHandler {
    //
    // The handler is provide with a AmazonWebServicesClientProxy that provides
    // the framework for making calls that returns a ProgressEvent,
    // which can then be chained to perform the next task.
    //
    protected ProgressEvent<ResourceModel, CallbackContext>
        handleRequest(final AmazonWebServicesClientProxy proxy,
                      final ResourceHandlerRequest<ResourceModel> request,
                      final CallbackContext callbackContext,
                      final ProxyClient<KinesisClient> client,
                      final Logger logger) {

        ResourceModel model = request.getDesiredResourceState();
        if (model.getName() == null || model.getName().isEmpty()) {
            model.setName(
               IdentifierUtils.generateResourceIdentifier(
                  "stream-", request.getClientRequestToken(), 128));
        }
        //
        // 1) initiate the call context, we are making createStream API call
        //
        return proxy.initiate(
            "kinesis:CreateStream", client, model, callbackContext)

            //
            // 2) transform Resource model properties to CreateStreamRequest API
            //
            .request((m) ->
                CreateStreamRequest.builder()
                    .streamName(m.getName()).shardCount(m.getShardCount()).build())

            //
            // 3) Make a service call. Handler does not worry about credentials, they
            //    are auto injected
            //
            .call((r, c) ->
                c.injectCredentialsAndInvokeV2(r, c.client()::createStream))

            //
            // provide stabilization callback. The callback is provided with
            // the following parameters
            //   a. CreateStreamRequest the we transformed in request()
            //   b. CreateStreamResponse that the service returned with successful call
            //   c. ProxyClient<Kinesis>, we provided in initiate call
            //   d. ResourceModel we provided in initiate call
            //   f. CallbackContext callback context.
            //
            //
            .stabilize((_request, _response, _client, _model, _context) ->
                 isStreamActive(client1, _model, context))

            //
            // Once ACTIVE return progress
            //
            .progress()

            //
            // we then chain to next state, setting tags on the resource.
            // we receive ProgressEvent object from .progress().
            //
            .then(r -> {
                Set<Tag> tags = model.getTags();
                if (tags != null && !tags.isEmpty()) {
                    return setTags(proxy, client, model, callbackContext, false, logger);
                }
                return r;
            })

            //
            // we then setRetention...
            //
            .then(r -> {
                Integer retention = model.getRetentionPeriodHours();
                if (retention != null) {
                    return handleRetention(proxy, client, model, DEFAULT_RETENTION, retention, callbackContext, logger);
                }
                return r;
            })

            ... // other steps

            //
            // finally we wait for Kinesis stream to be ACTIVE
            //
            .then((r) -> waitForActive(proxy, client, model, callbackContext))

            //
            // we then delete to ReadHandler to read the live state and send
            // back successful response.
            //
            .then((r) -> new ReadHandler()
                .handleRequest(proxy, request, callbackContext, client, logger));
    }
}
```

## How to Make Other Calls<a name="resource-type-develop-stabilize-other-calls"></a>

The same pattern shown here for CreateStreamRequest is followed with others as well\. Here is code for handleRetention:

```
protected ProgressEvent<ResourceModel, CallbackContext>
    handleRetention(final AmazonWebServicesClientProxy proxy,
                    final ProxyClient<KinesisClient> client,
                    final ResourceModel model,
                    final int previous,
                    final int current,
                    final CallbackContext callbackContext,
                    final Logger logger) {

       if (current > previous) {
            //
            // 1) initiate the call context, we are making IncreaseRetentionPeriod API call
            //
            return proxy.initiate(
                "kinesis:IncreaseRetentionPeriod:" + getClass().getSimpleName(),
                client, model, callbackContext)
                //
                // 2) transform Resource model properties to IncreaseStreamRetentionPeriodRequest API
                //
                .request((m) ->
                   IncreaseStreamRetentionPeriodRequest.builder()
                       .retentionPeriodHours(current)
                       .streamName(m.getName()).build())
                //
                // 3) Make a service call. Handler does not worry about credentials, they
                //    are auto injected

                // Add important comments like shown below
                // https://docs.aws.amazon.com/kinesis/latest/APIReference/API_IncreaseStreamRetentionPeriod.html
                // When applying change if stream is not ACTIVE, we get ResourceInUse.
                // We filter this expection back off and then re-try to set this.

                //
                // set new retention period
                //
                .call((r, c) -> c.injectCredentialsAndInvokeV2(r, c.client()::increaseStreamRetentionPeriod))

                //
                // Filter ResoureceInUse or LimitExceeded.
                // Currently LimitExceeded is issued even for throttles
                //
                .exceptFilter(this::filterException).progress();
        } else {
            return proxy.initiate("kinesis:DecreaseRetentionPeriod:" + getClass().getSimpleName(), client, model, callbackContext)
                //
                // convert to API model
                //
                .request(m -> DecreaseStreamRetentionPeriodRequest.builder().retentionPeriodHours(current).streamName(m.getName())
                    .build())
                ... // snipped for brevity
                .exceptFilter(this::filterException).progress();
        }
}

protected boolean filterException(AwsRequest request,
                                  Exception e,
                                  ProxyClient<KinesisClient> client,
                                  ResourceModel model,
                                  CallbackContext context) {
    return e instanceof ResourceInUseException ||
           e instanceof LimitExceededException;
}
```
