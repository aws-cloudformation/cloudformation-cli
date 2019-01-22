package com.aws.cfn.proxy;

import com.amazonaws.services.cloudformation.AmazonCloudFormation;
import com.amazonaws.services.cloudformation.model.OperationStatus;
import com.amazonaws.services.cloudformation.model.RecordHandlerProgressRequest;
import com.aws.cfn.LambdaModule;
import com.google.inject.Guice;
import com.google.inject.Inject;
import com.google.inject.Injector;
import org.json.JSONObject;

import java.util.Optional;

public class CloudFormationCallbackAdapter<T> implements CallbackAdapter<T> {

    private final AmazonCloudFormation cloudFormationClient;

    /**
     * This .ctor provided for Lambda runtime which will not automatically invoke Guice injector
     */
    public CloudFormationCallbackAdapter() {
        final Injector injector = Guice.createInjector(new LambdaModule());
        this.cloudFormationClient = injector.getInstance(AmazonCloudFormation.class);
    }

    /**
     * This .ctor provided for testing
     */
    @Inject
    public CloudFormationCallbackAdapter(final AmazonCloudFormation cloudFormationClient) {
        this.cloudFormationClient = cloudFormationClient;
    }

    @Override
    public void reportProgress(final String bearerToken,
                               final Optional<HandlerErrorCode> errorCode,
                               final ProgressStatus progressStatus,
                               final T resourceModel,
                               final String statusMessage) {
        final RecordHandlerProgressRequest request = new RecordHandlerProgressRequest()
            .withBearerToken(bearerToken)
            .withOperationStatus(translate(progressStatus))
            .withStatusMessage(statusMessage);

        if (resourceModel != null) {
            request.setResourceModel(new JSONObject(resourceModel).toString());
        }

        errorCode.ifPresent(handlerErrorCode -> request.setErrorCode(translate(handlerErrorCode)));

        // TODO: be far more fault tolerant, do retries, emit logs and metrics, etc.
        this.cloudFormationClient.recordHandlerProgress(request);

    }

    private com.amazonaws.services.cloudformation.model.HandlerErrorCode translate(final HandlerErrorCode errorCode) {
        switch (errorCode) {
            case AccessDenied:
                return com.amazonaws.services.cloudformation.model.HandlerErrorCode.AccessDenied;
            case InternalFailure:
                return com.amazonaws.services.cloudformation.model.HandlerErrorCode.InternalFailure;
            case InvalidCredentials:
                return com.amazonaws.services.cloudformation.model.HandlerErrorCode.InvalidCredentials;
            case InvalidRequest:
                return com.amazonaws.services.cloudformation.model.HandlerErrorCode.InvalidRequest;
            case NetworkFailure:
                return com.amazonaws.services.cloudformation.model.HandlerErrorCode.NetworkFailure;
            case NoOperationToPerform:
                return com.amazonaws.services.cloudformation.model.HandlerErrorCode.NoOperationToPerform;
            case NotFound:
                return com.amazonaws.services.cloudformation.model.HandlerErrorCode.NotFound;
            case NotReady:
                return com.amazonaws.services.cloudformation.model.HandlerErrorCode.NotReady;
            case NotUpdatable:
                return com.amazonaws.services.cloudformation.model.HandlerErrorCode.NotUpdatable;
            case ServiceException:
                return com.amazonaws.services.cloudformation.model.HandlerErrorCode.ServiceException;
            case ServiceLimitExceeded:
                return com.amazonaws.services.cloudformation.model.HandlerErrorCode.ServiceLimitExceeded;
            case ServiceTimeout:
                return com.amazonaws.services.cloudformation.model.HandlerErrorCode.ServiceTimeout;
            case Throttling:
                return com.amazonaws.services.cloudformation.model.HandlerErrorCode.Throttling;
            default:
                // InternalFailure is CloudFormation's fallback error code when no more specificity is there
                return com.amazonaws.services.cloudformation.model.HandlerErrorCode.InternalFailure;
        }
    }

    private com.amazonaws.services.cloudformation.model.OperationStatus translate(final ProgressStatus progressStatus) {
        switch (progressStatus) {
            case Complete:
                return OperationStatus.COMPLETE;
            case Failed:
                return OperationStatus.FAILED;
            case InProgress:
                return OperationStatus.IN_PROGRESS;
            default:
                // default will be to fail on unknown status
                return OperationStatus.FAILED;
        }
    }
}
