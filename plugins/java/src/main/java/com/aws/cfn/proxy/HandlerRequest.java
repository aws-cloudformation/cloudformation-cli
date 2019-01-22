package com.aws.cfn.proxy;

import com.aws.cfn.Action;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * This interface describes the request object for the provisioning request
 * @param <T> Type of resource model being provisioned
 */
@Data
@NoArgsConstructor
public class HandlerRequest<T> {
    private Action action;
    private String awsAccountId;
    private String bearerToken;
    private String nextToken;
    private String region;
    private String resourceType;
    private String resourceTypeVersion;
    private RequestData<T> requestData;
    private String stackId;
    private RequestContext requestContext;
}
