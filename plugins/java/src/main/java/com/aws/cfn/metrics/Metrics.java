package com.aws.cfn.metrics;

public class Metrics {

    public final static String METRIC_NAMESPACE_ROOT = "AWS_TMP/CloudFormation";
    public final static String METRIC_NAME_HANDLER_EXCEPTION = "HandlerException";
    public final static String METRIC_NAME_HANDLER_DURATION = "HandlerInvocationDuration";
    public final static String METRIC_NAME_HANDLER_INVOCATION_COUNT = "HandlerInvocationCount";

    public final static String DIMENSION_KEY_ACTION_TYPE = "Action";
    public final static String DIMENSION_KEY_EXCEPTION_TYPE = "ExceptionType";
    public final static String DIMENSION_KEY_RESOURCE_TYPE = "ResourceType";
}
