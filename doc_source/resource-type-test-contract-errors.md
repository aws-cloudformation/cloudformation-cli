# Handler error codes<a name="resource-type-test-contract-errors"></a>

One of the following error codes MUST be returned from the handler whenever there is a [progress event](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-test-progressevent.html) with an operation status of `FAILED`\.
+ `AccessDenied`

  The customer has insufficient permissions to perform this request\.

  *Type:* Terminal
+ `AlreadyExists`

  The specified resource already existed prior to the execution of this handler\. This error is applicable to `create` handlers only\.

  *Type:* Terminal
+ `GeneralServiceException`

  The downstream service generated an error that does not map to any other handler error code\.

  *Type:* Terminal
+ `InternalFailure`

  An unexpected error occurred within the handler\.

  *Type:* Terminal
+ `InvalidCredentials`

  The credentials provided by the user are invalid\.

  *Type:* Terminal
+ `InvalidRequest`

  Invalid input from the user has generated a generic exception\.

  *Type:* Terminal
+ `NetworkFailure`

  The request could not be completed due to networking issues, such as a failure to receive a response from the server\.

  *Type:* Retriable
+ `NotFound`

  The specified resource does not exist, or is in a terminal, inoperable, and irrecoverable state\.

  *Type:* Terminal
+ `NotStabilized`

  The downstream resource failed to complete all of its ready\-state checks\.

  *Type:* Retriable
+ `NotUpdatable`

  The user has requested an update to a property defined in the resource type schema as a [create\-only property](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-schema.html#schema-properties-createonlyproperties)\. This error is applicable to `update` handlers only\.

  *Type:* Terminal
+ `ResourceConflict`

  The resource is temporarily unavailable to be acted upon\. For example, if the resource is currently undergoing an operation and cannot be acted upon until that operation is finished\. 

  *Type:* Retriable
+ `ServiceInternalError`

  The downstream service returned an internal error, typically with a `5XX` HTTP Status code\.

  *Type:* Retriable
+ `ServiceLimitExceeded`

  A non\-transient resource limit was reached on the service side\.

  *Type:* Terminal
+ `Throttling`

  The request was throttled by a downstream service\. Retriable\.

  *Type:* Retriable