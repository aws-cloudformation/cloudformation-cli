# ProgressEvent object schema<a name="resource-type-test-progressevent"></a>

A `ProgressEvent` is a JSON object which represents the current operation status of the handler, the current live state of the resource, and any additional resource information the handler wishes to communicate to the CloudFormation CLI\. Each handler MUST communicate a progress event to the CloudFormation CLI under certain circumstances, and SHOULD communicate a progress event under others\. For more information, see [Handler Communication Contract](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-contract.html#resource-type-test-contract-communication)\.

A handler MAY use progress events on a re\-invocation to continue work from where it left off\. For a detailed discussion of this, see [Progress Chaining, Stabilization and Callback Pattern](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-develop-stabilize.html)\.

## Syntax<a name="resource-type-test-progressevent-syntax"></a>

Below is the syntax for the ProgressEvent object\.

```
{
    "OperationStatus": "string",
    "HandlerErrorCode": "string",
    "Message": "string",
    "CallbackContext": "string",
    "CallbackDelaySeconds": "string",
    "ResourceModel": "string",
    "ResourceModels": [
        "string"
    ],
    "NextToken": "string",
    }
```

## Properties<a name="resource-type-schema-properties"></a>

`OperationStatus`  <a name="progressevent-properties-OperationStatus"></a>
Indicates whether the handler has reached a terminal state or is still computing and requires more time to complete\.
Values: `PENDING` \| `IN_PROGRESS` \| `SUCCESS` \| `FAILED`
 *Required*: No

`HandlerErrorCode`  <a name="progressevent-properties-HandlerErrorCode"></a>
A handler error code should be provided when the event operation status is `FAILED` or `IN_PROGRESS`\.
For a list of handler error codes, see [Handler Error Codes](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-contract-errors.html)\.
 *Required*: Conditional\. A handler error codes MUST be returned from the handler whenever there is a progress event with an operation status of `FAILED`\.

`Message`  <a name="progressevent-properties-Message"></a>
Information which can be shown to users to indicate the nature of a progress transition or callback delay\.
 *Required*: No

`CallbackContext`  <a name="progressevent-properties-CallbackContext"></a>
Arbitrary information which the handler can return in an event with operation status of `IN_PROGRESS`, to allow the passing through of additional state or metadata between subsequent retries\. For example, to pass through a resource identifier which can be used to continue polling for stabilization\.
For more detailed examples, see [Progress Chaining, Stabilization and Callback Pattern](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-develop-stabilize.html)\.
 *Required*: No

`CallbackDelaySeconds`  <a name="progressevent-properties-CallbackDelaySeconds"></a>
A callback will be scheduled with an initial delay of no less than the number of seconds specified\.
Set this value to less than 0 to indicate no callback should be made\.
 *Required*: No

`ResourceModel`  <a name="progressevent-properties-ResourceModel"></a>
Resource model returned by a `read` or `list` operation response for synchronous results, or for final response validation/confirmation by `create`, `update`, and `delete` operations\.
 *Required*: No

`ResourceModels`  <a name="progressevent-properties-ResourceModels"></a>
List of resource models returned by a `list` operation response for synchronous results\.
 *Required*: Conditional\. Required for List handlers\.

`NextToken`  <a name="progressevent-properties-NextToken"></a>
Token used to request additional pages of resources from a `list` operation response\.
 *Required*: Conditional\. Required for List handlers\.
