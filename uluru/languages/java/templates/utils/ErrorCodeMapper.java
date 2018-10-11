package {{ packageName }}.utils;

import {{ packageName }}.messages.ErrorCode;
import {{ packageName }}.messages.HandlerRequest;


import static {{ packageName }}.messages.ErrorCode.*;

/**
 * This class maps service error codes to CloudFormation error codes
 */
public class ErrorCodeMapper {

    public static ErrorCode mapError(final HandlerRequest request, final Exception e) {
        if (isInvalidRequest(request, e))
            return InvalidRequest;

        if (isAccessDenied(request, e))
            return AccessDenied;

        if (isInvalidCredentials(request, e))
            return InvalidCredentials;

        if (isNoOperationToPerform(request, e))
            return NoOperationToPerform;

        if (isNotUpdatable(request, e))
            return NotUpdatable;

        if (isNotFound(request, e))
            return NotFound;

        if (isNotReady(request, e))
            return NotReady;

        if (isThrottling(request, e))
            return Throttling;

        if (isServiceLimitExceeded(request, e))
            return ServiceLimitExceeded;

        if (isServiceTimeout(request, e))
            return ServiceTimeout;

        if (isServiceException(request, e))
            return ServiceException;

        if (isNetworkFailure(request, e))
            return NetworkFailure;

        /** an unexpected error occurred within the handler, such as an NPE, etc. */
        return InternalFailure;
    }

    /**
     * a generic exception caused by invalid input from the customer
     */
    private static boolean isInvalidRequest(final HandlerRequest request, final Exception e) {
        return false;
    }

    /**
     * the customer has insufficient permissions to perform this action
     */
    private static boolean isAccessDenied(final HandlerRequest request, final Exception e) {
        return false;
    }

    /**
     * the customer's provided credentials were invalid
     */
    private static boolean isInvalidCredentials(final HandlerRequest request, final Exception e) {
        return false;
    }

    /**
     * the handler completed without making any modifying API calls (only applicable to Update handler)
     */
    private static boolean isNoOperationToPerform(final HandlerRequest request, final Exception e) {
        return false;
    }

    /**
     * the customer tried perform an update to a property that is not updatable (only applicable to UpdateHandler)
     */
    private static boolean isNotUpdatable(final HandlerRequest request, final Exception e) {
        return false;
    }

    /**
     * the specified resource does not exist, or is in a terminal, inoperable, and irrecoverable state
     */
    private static boolean isNotFound(final HandlerRequest request, final Exception e) {
        return false;
    }

    /**
     * the resource is temporarily in an inoperable state
     */
    private static boolean isNotReady(final HandlerRequest request, final Exception e) {
        return false;
    }

    /**
     * the request was throttled by the downstream service.
     * Handlers SHOULD retry on service throttling using exponential backoff in order to be resilient to transient throttling.
     */
    private static boolean isThrottling(final HandlerRequest request, final Exception e) {
        return false;
    }

    /**
     * a non-transient resource limit was reached on the service side
     */
    private static boolean isServiceLimitExceeded(final HandlerRequest request, final Exception e) {
        return false;
    }

    /**
     * the handler timed out waiting for the downstream service to perform an operation
     */
    private static boolean isServiceTimeout(final HandlerRequest request, final Exception e) {
        return false;
    }

    /**
     * a generic exception from the downstream service
     */
    private static boolean isServiceException(final HandlerRequest request, final Exception e) {
        return false;
    }

    /**
     * the request was unable to be completed due to networking issues, such as failure to receive a response from the server.
     * Handlers SHOULD retry on network failures using exponential backoff in order to be resilient to transient issues.
     */
    private static boolean isNetworkFailure(final HandlerRequest request, final Exception e) {
        return false;
    }
}
