package com.aws.cfn;

import com.aws.cfn.proxy.ProgressStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import org.json.JSONObject;

@Data
public class Response {
    private static final String STATUS = "status";
    private static final String MESSAGE = "message";
    private static final String RESOURCE_MODEL = "resourceModel";

    /**
     * The status indicates whether the handler has reached a terminal state or
     * is still computing and requires more time to complete
     */
    @JsonProperty(STATUS)
    private ProgressStatus status;

    /**
     * The handler can (and should) specify a contextual information message which
     * can be shown to callers to indicate the nature of a progress transition
     * or callback delay; for example a message indicating "propagating to edge"
     */
    @JsonProperty(MESSAGE)
    private String message;

    /**
     * The output resource instance populated by a READ/LIST for synchronous results
     * and by CREATE/UPDATE/DELETE for final response validation/confirmation
     */
    @JsonProperty(RESOURCE_MODEL)
    private JSONObject resourceModel;
}
