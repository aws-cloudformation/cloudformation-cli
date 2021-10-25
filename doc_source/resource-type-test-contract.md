# Resource type handler contract<a name="resource-type-test-contract"></a>

The resource type handler contract specifies the expected and required behavior to which a resource must adhere in each given event handler\. It defines a set of specific, unambiguous rules with which `create`, `read`, `update`, `delete` and `list` resource handlers must comply\. Following the contract will allow customers to interact with all resource types under a uniform set of behaviors and expectations, and prevents creation of unintended or duplicate resources\.

A resource implementation MUST pass all resource contract tests in order to be registered\.

Assuming no other concurrent interaction on the resource, the handlers MUST comply with the following contract\.

All terminology in the handler contract requirements adheres to the [RFC 2119 specification](https://www.ietf.org/rfc/rfc2119.txt)\.

## Create handlers<a name="resource-type-test-contract-create"></a>

### Input assumptions<a name="resource-type-test-contract-create-in"></a>

The `create` handler can make the following assumptions about input submitted to it:
+ The input to a `create` handler MUST be valid against the resource schema\.

### Output requirements<a name="resource-type-test-contract-create-out.title"></a>

The `create` handler must adhere to the following requirements regarding its output:
+ A `create` handler MUST always return a ProgressEvent object within 60 seconds\. For more information, see [ProgressEvent Object Schema](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-progressevent.html)\.

  In every ProgressEvent object, the `create` handler MUST return a model which conforms to the shape of the resource schema\. For more information, see [Returned models must conform to the shape of the schema](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-contract.html#resource-type-test-contract-additional-shape)\.

  Every model MUST include the primaryIdentifier\. The only exception is if the first progress event is `FAILED`, and the resource has not yet been created\. In this case, a subsequent `read` call MUST return `NotFound`\.
+ A `create` handler MUST NOT return `SUCCESS` until it has applied all properties included in the `create` request\. For more information, see [Update, create, and delete handlers must satisfy desired\-state stabilization](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-contract.html#resource-type-test-contract-additional-stabilization)\.
  + A `create` handler MUST return IN\_PROGRESS if it has not yet reached the desired\-state\.

    A `create` handler SHOULD return a model containing all properties set so far and nothing more during each IN\_PROGRESS event\.
  + A `create` handler MUST return FAILED progress event if it cannot reach the desired\-state within the timeout specified in the resource schema\.

    The progress event MUST return an error message and the most applicable error code\. For more information, see [Handler error codes](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-contract-errors.html)\.
  + A `create` handler MAY return SUCCESS once it reaches the desired\-state\.

    Once the desired state has been reached, a `create` handler MAY perform runtime\-state stabilization\. For more information, see [Update and create handlers should satisfy runtime\-state stabilization](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-contract.html#resource-type-test-contract-additional-runtime)\.

    When the `create` handler returns SUCCESS, it MUST return a ProgressEvent object containing a model that satisfies the following requirements:
    + All properties specified in the `create` request MUST be present in the model returned, and they MUST match exactly, with the exception of properties defined as writeOnlyProperties in the resource schema\.
    + The model MUST contain all properties that have values, including any properties that have default values, and any readOnlyProperties as defined in the resource schema\.
    + The model MUST NOT return any properties that are null or do not have values\.
+ After a `create` operation returns SUCCESS, a subsequent `read` request MUST succeed when passed in the primaryIdentifier or any additionalIdentifiers associated with the provisioned resource instance\.
+ After a `create` operation returns SUCCESS, a subsequent `list` operation MUST return the primaryIdentifier associated with the provisioned resource instance\.

  If the `list` operation is paginated, the entire `list` operation is defined as all `list` requests until the `nextToken` is `null`\.
+ A `create` handler MUST be idempotent\. A `create` handler MUST NOT create multiple resources given the same idempotency token\.
+ A `create` handler MUST return FAILED with an AlreadyExists error code if the resource already existed prior to the create request\.

## Update handlers<a name="resource-type-test-contract-update"></a>

### Input assumptions<a name="resource-type-test-contract-update-in"></a>

The `update` handler can make the following assumptions about input submitted to it:
+ The input to an `update` handler MUST be valid against the resource schema\.
+ Any `createOnlyProperties` specified in update handler input MUST NOT be different from their previous state\.
+ The input to an `update` handler MUST contain either the `primaryIdentifier` or an `additionalIdentifier`\.

### Output requirements<a name="resource-type-test-contract-update-out.title"></a>

The `update` handler must adhere to the following requirements:
+ An `update` handler MUST always return a ProgressEvent object within 60 seconds\. For more information, see [ProgressEvent Object Schema](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-progressevent.html)\.

  In every ProgressEvent object, the `update` handler MUST return a model which conforms to the shape of the resource schema\. For more information, see [Returned models must conform to the shape of the schema](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-contract.html#resource-type-test-contract-additional-shape)\.

  Every model MUST include the primaryIdentifier\.

  The primaryIdentifier returned in every progress event must match the primaryIdentifier passed into the request\.
+ An `update` handler MUST NOT return `SUCCESS` until it has applied all properties included in the `update` request\. For more information, see [Update, create, and delete handlers must satisfy desired\-state stabilization](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-contract.html#resource-type-test-contract-additional-stabilization)\.
  + An `update` handler MUST return IN\_PROGRESS if it has not yet reached the desired\-state\.

    An `update` handler SHOULD return a model containing all properties set so far and nothing more during each IN\_PROGRESS event\.
  + An `update` handler MUST return FAILED progress event if it cannot reach the desired\-state within the timeout specified in the resource schema\.

    The progress event MUST return an error message and the most applicable error code\. For more information, see [Handler error codes](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-contract-errors.html)\.
  + An `update` handler MAY return SUCCESS once it reaches the desired\-state\.

    Once the desired state has been reached, an `update` handler MAY perform runtime\-state stabilization\. For more information, see [Update and create handlers should satisfy runtime\-state stabilization](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-contract.html#resource-type-test-contract-additional-runtime)\.

    When the `update` handler returns SUCCESS, it MUST return a ProgressEvent object containing a model that satisfies the following requirements:
    + All properties specified in the `update` request MUST be present in the model returned, and they MUST match exactly, with the exception of properties defined as writeOnlyProperties in the resource schema\.
    + The model MUST contain all properties that have values, including any properties that have default values, and any readOnlyProperties as defined in the resource schema\.
    + The model MUST NOT return any properties that are null or do not have values\.

  All list or collection properties MUST be applied in full\. The successful outcome MUST be replacement of the previous properties, if any\.
+ An `update` handler MUST return FAILED with a `NotFound` error code if the resource did not exist prior to the `update` request\.
+ An `update` handler MUST NOT create a new physical resource\.

## Delete handlers<a name="resource-type-test-contract-delete"></a>

### Input assumptions<a name="resource-type-test-contract-delete-in"></a>

The `delete` handler can make the following assumptions about input submitted to it:
+ The input to a `delete` handler MUST contain either the `primaryIdentifier` or an `additionalIdentifier`\. Any other properties MAY NOT be included in the request\.

### Output requirements<a name="resource-type-test-contract-delete-out.title"></a>

The `delete` handler must adhere to the following requirements:
+ A `delete` handler MUST always return a ProgressEvent object within 60 seconds\. For more information, see [ProgressEvent Object Schema](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-progressevent.html)\.
+ A `delete` handler MUST NOT return `SUCCESS` until the resource has reached the desired state for deletion\. For more information, see [Update, create, and delete handlers must satisfy desired\-state stabilization](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-contract.html#resource-type-test-contract-additional-stabilization)\.
  + A `delete` handler MUST return IN\_PROGRESS if it has not yet reached the desired state\.
  + A `delete` handler MUST return FAILED progress event if it cannot reach the desired\-state within the timeout specified in the resource schema\.

    The progress event MUST return an error message and the most applicable error code\. For more information, see [Handler error codes](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-contract-errors.html)\.
  + A `delete` handler MUST return SUCCESS once it reaches the desired state\. \(This is because there is no runtime\-state stabilization for delete requests\.\)

    When the `delete` handler returns SUCCESS, the ProgressEvent object MUST NOT contain a model\.
+ A `delete` hander MUST return FAILED with a `NotFound` error code if the resource didn't exist prior to the delete request\.
+ Once a `delete` operation successfully completes, any subsequent `update`, `delete`, or `read` request for the deleted resource instance MUST return `FAILED` with a `NotFound` error code\.
+ Once a `delete` operation successfully completes, any subsequent `list` operation MUST NOT return the primaryIdentifier associated with the deleted resource instance\.

  If the `list` operation is paginated, the 'list operation' is defined as all `list` calls until the `nextToken` is `null`\.
+ Once a `delete` operation successfully completes, a subsequent `create` request with the same primaryIdentifier or additionalIdentifiers MUST NOT return `FAILED` with an `AlreadyExists` error code\.
+ Once a `delete` operation successfully completes, the resource SHOULD NOT be billable to the customer\.

## Read handlers<a name="resource-type-test-contract-read"></a>

### Input assumptions<a name="resource-type-test-contract-read-in"></a>

The `read` handler can make the following assumptions about input submitted to it:
+ The input to a `read` handler MUST contain either the `primaryIdentifier` or an `additionalIdentifier`\. Any other properties MAY NOT be included in the request\.

### Output requirements<a name="resource-type-test-contract-read-out.title"></a>

The `read` handler must adhere to the following requirements regarding its output:
+ A `read` handler MUST always return a ProgressEvent object within 30 seconds\. For more information, see [ProgressEvent Object Schema](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-progressevent.html)\.

  A `read` handler MUST always return a status of `SUCCESS` or `FAILED`; it MUST NOT return a status of `IN_PROGRESS`\.
+ A `read` handler MUST return a model representation that conforms to the shape of the resource schema\.
  + The model MUST contain all properties that have values, including any properties that have default values and any `readOnlyProperties` as defined in the resource schema\.
  + The model MUST NOT return any properties that are null or do not have values\.
+ A `read` handler MUST return `FAILED` with a `NotFound` error code if the resource does not exist\.

## List handlers<a name="resource-type-test-contract-list"></a>
+ A `list` handler MUST always return a ProgressEvent object within 30 seconds\. For more information, see [ProgressEvent Object Schema](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-progressevent.html)\.

  A `list` handler MUST always return a status of `SUCCESS` or `FAILED`; it MUST NOT return a status of `IN_PROGRESS`\.
+ A `list` handler MUST return an array of primary identifiers\.

  When passed in a `read` request, each `primaryIdentifier` MUST NOT return `FAILED` with `NotFound` error code\.
+ A `list` request MUST support pagination by returning a `NextToken`\.

  The `NextToken` returned MUST be able to be used in a subsequent `list` request to retrieve the next set of results from the service\.

  The `NextToken` MUST be null when all results have been returned\.
+ A `list` request MUST return an empty array if there are no resources found\.
+ A `list` handler MAY accept a set of properties conforming to the shape of the resource schema as filter criteria\.

  The filter should use `AND(&)` when multiple properties are passed in\.

## Additional requirements<a name="resource-type-test-contract-additional"></a>

The following requirements also apply to resource handlers\.

### Returned models must conform to the shape of the schema<a name="resource-type-test-contract-additional-shape"></a>

A model returned in a [ProgressEvent](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-progressevent.html) object MUST always conform to the shape of the resource schema\. This means that each property that is returned MUST adhere to its own individual restrictions: correct data type, regex, length, etc\. However, the model returned MAY NOT contain all properties defined as required in the json\-schema\.

More specifically, contract tests validate models based on json\-schema [Validation Keywords](https://json-schema.org/draft-07/json-schema-validation.html#rfc.section.6)\.
+ ALL Validation Keywords for the following MUST be observed:
  + Any Instance Type \(Section 6\.1\)
  + Numeric Instances \(Section 6\.2\)
  + Strings \(Section 6\.3\)
  + Arrays \(Section 6\.4\)
+ All Validation Keywords for Objects \(Section 6\.5\) MUST be observed EXCEPT for:
  + required \(Section 6\.5\.3\)
  + dependencies \(Section 6\.5\.7\)
  + propertyNames \(Section 6\.5\.8\)
+ Contract tests won't validate Validation Keywords for:
  + Applying Subschemas Conditionally \(Section 6\.6\)
  + Applying Subschemas With Boolean Logic \(Section 6\.7\)

### Update, create, and delete handlers must satisfy desired\-state stabilization<a name="resource-type-test-contract-additional-stabilization"></a>

Stabilization is the process of waiting for a resource to be in a particular state\. Note that reaching the desired\-state is mandatory for all handlers before returning SUCCESS\.

#### Create and update handlers<a name="resource-type-test-contract-additional-stabilization-create"></a>

For Create and Update handlers, desired\-state stabilization is satisfied when all properties specified in the request are applied as requested\. This is verified by calling the Read handler\.

In many cases, the desired\-state is reached immediately upon completion of a Create/Update API call\. However, in some cases, multiple API calls and or wait periods may be required in order to reach this state\.

##### Eventual consistency in desired\-state stabilization<a name="resource-type-test-contract-additional-stabilization-consistency"></a>

Eventual consistency means that the result of an API command you run might not be immediately visible to all subsequent commands you run\. Handling API eventual consistency is required as part of desired\-state stabilization\. This is because a subsequent Read call might fail with a NotFound error code\.

Amazon EC2 resources are a great example of this\. For more information, see [Eventual Consistency](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/query-api-troubleshooting.html#eventual-consistency) in the *Amazon Elastic Compute Cloud API Reference\.*

##### Examples of desired\-state stabilization<a name="resource-type-test-contract-additional-stabilization-examples"></a>

For a simple example of desired\-state stabilization, consider the implementation of the `create` handler for the `AWS::Logs::MetricFilter` resource: immediately after the handler code completes the call to the `PutMetricFilter` method, the `AWS::Logs::MetricFilter` has achieved its desired state\. You can examine the code for this resource in its open\-source repository at [github\.com/aws\-cloudformation/aws\-cloudformation\-resource\-providers\-logs](https://github.com/aws-cloudformation/aws-cloudformation-resource-providers-logs)\.

A more complex example is the implementation of the `update` handler for the `AWS::Kinesis::Stream` resource\. The `update` handler must make multiple API calls during an update, including `AddTagsToStream` or `RemoveTagsFromStream`, `UpdateShardCount`, `IncreaseRetentionPeriod` or `DecreaseRetentionPeriod`, and `StartStreamEncryption` or `StopStreamEncryption`\. Meanwhile, each API call will set the `StreamStatus` to `UPDATING`, during which time other API calls cannot be performed or the API will throw a `ResourceInUseException`\. Therefore, in order to reach the desired state, the handler will need to wait for the `StreamStatus` to become `ACTIVE` in between each API call\.

#### Delete handlers<a name="resource-type-test-contract-additional-stabilization-delete"></a>

In most cases, the definition of 'deleted' is obvious\. A `delete` API call will result in the resource being purged from the database, and the resource is no longer describable to the user\.

However, in some cases, a deletion will result in the resource leaving an *audit trail*, in which the resource can still be described by service APIs, but can no longer be interacted with by the user\. For example, when you delete a CloudFormation stack, it is assigned a status of `DELETE_COMPLETE`, but it can still be returned from a `[DescribeStacks](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeStacks.html)` API call\. For resources like this, the desired\-state for deletion is when the resource has reached a *terminal, inoperable, and irrecoverable state*\. If the resource can continue to be mutated by the user through another API call, then it is not *deleted*, it is *updated*\.

Note that there is no difference between desired\-state stabilization and runtime\-state stabilization for a delete handler\. By definition, once a resource has reached the desired\-state for deletion, a subsequent `read` call MUST return `FAILED` with a `NotFound` error code, and a subsequent `create` call with the same primaryIdentifier or additionalIdentifiers MUST NOT return `FAILED` with an `AlreadyExists` error code\. Additional restrictions are defined in the contract above\.

So in the case of a CloudFormation stack, a `read` handler MUST return `FAILED` with a `NotFound` error code if the stack is `DELETE_COMPLETE`, even though it's audit trail can still be accessed by the DescribeStacks API\.

### Update and create handlers should satisfy runtime\-state stabilization<a name="resource-type-test-contract-additional-runtime"></a>

*Runtime\-state stabilization* is a process of waiting for the resource to be "ready" to use\. Generally, runtime\-state stabilization is done by continually describing the resource until it reaches a particular state, though it can take many forms\.

Runtime\-state stabilization can mean different things for different resources, but the following are common requirements:
+ *Additional mutating API calls can be made on the resource*

  Some resources cannot be modified while they are in a particular state
+ *Dependent resources can consume the resource*

  There may be other resources which need to consume the resource in some way, but can't until it is in a particular state\.
+ *Users can interact with the resource*

  Customers may not be able to use the resource until it is in a particular status\. This usually overlaps with the dependent resources requirement, although there could be different qualifications, depending on the resources\.

Note that while desired\-state stabilization is mandatory, runtime\-state stabilization is optional but encouraged\. Users have come to expect that once a resource is COMPLETE, they will be able to use it\.

#### Examples of run\-time stabilization<a name="resource-type-test-contract-additional-runtime-examples"></a>

For a simple example of run\-time stabilization, consider the implementation of the `create` handler for the `AWS::KinesisFirehose::DeliveryStream` resource\. The `create` handler invokes only a single API, `CreateDeliveryStream`, in order for the resource to reach its desired state\. Immediately after this API call is made, a `read` request will return the correct desired state\. However, the resource still has not reached run\-time stabilization because it cannot be used by the customer or downstream resources until the `DeliveryStreamStatus` is `ACTIVE`\.

For a more complex example, consider the implementation of the `update` handler for the `AWS::Kinesis::Stream` resource once again\. Once the `update` handler has made its final call, to `StartStreamEncryption` or `StopStreamEncryption` as described in [Examples of desired\-state stabilization](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-contract.html#resource-type-test-contract-additional-stabilization-examples), the resource has reached its desired state\. However, like the other API calls on the Kinesis resource, the `StreamStatus` will again be set to `UPDATING`\. During this period, it has reached its desired state, and customers can even continue using the stream\. But it has not yet achieved runtime\-stabilization, because additional API calls cannot be made on the resource until the `StreamStatus` gets set to `ACTIVE`\.

### Handlers must not leak resources<a name="resource-type-test-contract-additional-leaking"></a>

*Resource leaking* refers to when a handler loses track of the existence of a resource\. This happens most often in the following cases:
+ A `create` handler is not idempotent\. Re\-invoking the handler with the same idempotencyToken will cause another resource to be created, and the handler is only tracking a single resource\.
+ A `create` handler creates the resource, but is unable to communicate an identifier for that resource back to CloudFormation\. A subsequent `delete` call does not have enough information to delete the resource\.
+ A bug in the `delete` handler causes the resource to not actually be deleted, but the `delete` handler reports that the resource was successfully deleted\.