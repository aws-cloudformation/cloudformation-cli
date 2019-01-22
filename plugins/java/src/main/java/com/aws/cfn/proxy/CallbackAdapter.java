package com.aws.cfn.proxy;

import java.util.Optional;

/**
 * Interface used to abstract the function of reporting back provisioning progress to the handler caller
 */
public interface CallbackAdapter<T> {

    void reportProgress(final String bearerToken,
                        final Optional<HandlerErrorCode> errorCode,
                        final ProgressStatus progressStatus,
                        final T resourceModel,
                        final String statusMessage);

}
