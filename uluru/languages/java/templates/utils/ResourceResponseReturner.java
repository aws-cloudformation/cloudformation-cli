package {{ packageNamePrefix }}.utils;

import com.amazon.cloudformation.selfservice.exception.TerminalException;
import com.amazon.cloudformation.selfservice.messages.*;
import com.amazonaws.AmazonServiceException;

import static com.amazon.cloudformation.selfservice.utils.Constants.INTERNAL_FAILURE_MESSAGE;


public class ResourceResponseReturner {

    public static ResourceResponse handleSuccess(final String physicalResourceId, final Boolean modified, final String clientRequestToken) {
        return new ResourceResponse()
            .withStatus(Status.SUCCESS)
            .withModified(modified)
            .withResponseData(new ResponseData().withPhysicalResourceId(physicalResourceId))
            .withClientRequestToken(clientRequestToken);
    }

    public static ResourceResponse handleFailure(final String physicalResourceId, final Boolean modified, final String clientRequestToken) {
        return new ResourceResponse()
            .withStatus(Status.FAILURE)
            .withModified(modified)
            .withResponseData(new ResponseData().withPhysicalResourceId(physicalResourceId))
            .withClientRequestToken(clientRequestToken);
    }

    public static ResourceResponse handleRetry(final String physicalResourceId, final Boolean modified, final String clientRequestToken) {
        return new ResourceResponse()
            .withStatus(Status.RETRY)
            .withModified(modified)
            .withResponseData(new ResponseData().withPhysicalResourceId(physicalResourceId))
            .withClientRequestToken(clientRequestToken);
    }

    public static ResourceResponse handleDefaultError(final Throwable e, final String physicalResourceId, final Boolean modified, final String clientRequestToken) {
        ResourceResponse response = new ResourceResponse().withClientRequestToken(clientRequestToken)
            .withResponseData(new ResponseData().withPhysicalResourceId(physicalResourceId));

        if (modified != null) {
            response.setModified(modified);
        }

        if (e instanceof AmazonServiceException) {
            int errorStatus = ((AmazonServiceException) e).getStatusCode();
            if (errorStatus >= 400 && errorStatus < 500) {
                // 400s default to FAILURE
                response.setMessage(e.getMessage());
                response.setStatus(Status.FAILURE);
            } else {
                // 500s default to RETRY
                response.setModified(true);
                response.setStatus(Status.RETRY);
            }
            response.setMessage(e.getMessage());
        } else if (e instanceof TerminalException) {
            response.setMessage(e.getMessage());
            response.setStatus(Status.FAILURE);
        } else {
            // Unexpected exceptions default to be InternalFailure
            response.setMessage(INTERNAL_FAILURE_MESSAGE);
            response.setStatus(Status.FAILURE);
        }
        return response;
    }

}
