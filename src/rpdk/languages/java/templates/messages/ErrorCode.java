package {{ packageName }}.messages;

/**
 * One of the following error codes MUST be returned from handlers when there is a FAILED progress event.
 * Any error codes from the service should be returned separately as part of the error message.
 */
public enum ErrorCode {
    /** a generic exception caused by invalid input from the customer */
    InvalidRequest,

    /** the customer has insufficient permissions to perform this action */
    AccessDenied,

    /** the customer's provided credentials were invalid */
    InvalidCredentials,

    /** the handler completed without making any modifying API calls (only applicable to Update handler) */
    NoOperationToPerform,

    /** the customer tried perform an update to a property that is not updatable (only applicable to UpdateHandler) */
    NotUpdatable,

    /** the specified resource does not exist, or is in a terminal, inoperable, and irrecoverable state */
    NotFound,

    /** the resource is temporarily in an inoperable state */
    NotReady,

    /** the request was throttled by the downstream service.  Handlers SHOULD retry on service throttling using exponential backoff in order to be resilient to transient throttling.  */
    Throttling,

    /** a non-transient resource limit was reached on the service side */
    ServiceLimitExceeded,

    /** the handler timed out waiting for the downstream service to perform an operation */
    ServiceTimeout,

    /** a generic exception from the downstream service */
    ServiceException,

    /** the request was unable to be completed due to networking issues, such as failure to receive a response from the server.  Handlers SHOULD retry on network failures using exponential backoff in order to be resilient to transient issues. */
    NetworkFailure,

    /** an unexpected error occurred within the handler, such as an NPE, etc. */
    InternalFailure
}
