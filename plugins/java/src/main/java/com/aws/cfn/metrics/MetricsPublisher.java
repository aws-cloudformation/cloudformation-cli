package com.aws.cfn.metrics;

import com.aws.cfn.Action;

import java.util.Date;

public interface MetricsPublisher {

    String getResourceTypeName();
    void setResourceTypeName(String resourceTypeName);

    void publishExceptionMetric(final Date timestamp,
                                final Action action,
                                final Exception e);

    void publishInvocationMetric(final Date timestamp,
                                 final Action action);

    void publishDurationMetric(final Date timestamp,
                               final Action action,
                               long milliseconds);
}
