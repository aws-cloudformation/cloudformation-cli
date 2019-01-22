package com.aws.cfn.metrics;

import com.amazonaws.services.cloudwatch.AmazonCloudWatch;
import com.amazonaws.services.cloudwatch.model.Dimension;
import com.amazonaws.services.cloudwatch.model.MetricDatum;
import com.amazonaws.services.cloudwatch.model.PutMetricDataRequest;
import com.amazonaws.services.cloudwatch.model.StandardUnit;
import com.aws.cfn.Action;
import com.aws.cfn.LambdaModule;
import com.google.inject.Guice;
import com.google.inject.Inject;
import com.google.inject.Injector;

import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class MetricsPublisherImpl implements MetricsPublisher {

    private final AmazonCloudWatch amazonCloudWatch;
    private String resourceNamespace;
    private String resourceTypeName;

    /**
     * This .ctor provided for Lambda runtime which will not invoke Guice injector
     */
    public MetricsPublisherImpl() {
        final Injector injector = Guice.createInjector(new LambdaModule());
        this.amazonCloudWatch = injector.getInstance(AmazonCloudWatch.class);
    }

    /**
     * This .ctor provided for testing
     * @param amazonCloudWatch
     */
    @Inject
    public MetricsPublisherImpl(final AmazonCloudWatch amazonCloudWatch) {
        this.amazonCloudWatch = amazonCloudWatch;
    }

    public String getResourceTypeName() {
        return this.resourceTypeName;
    }

    public void setResourceTypeName(final String resourceTypeName) {
        this.resourceTypeName = resourceTypeName;
        this.resourceNamespace = resourceTypeName.replace("::", "/");
    }

    public void publishExceptionMetric(final Date timestamp,
                                       final Action action,
                                       final Exception e) {
        final Map<String, String> dimensions = new HashMap<>();
        dimensions.put(Metrics.DIMENSION_KEY_ACTION_TYPE, action.name());
        dimensions.put(Metrics.DIMENSION_KEY_EXCEPTION_TYPE, e.getClass().toString());
        dimensions.put(Metrics.DIMENSION_KEY_RESOURCE_TYPE, this.getResourceTypeName());

        publishMetric(Metrics.METRIC_NAME_HANDLER_EXCEPTION,
            dimensions,
            StandardUnit.Count,
            1.0,
            timestamp);
    }

    public void publishInvocationMetric(final Date timestamp,
                                        final Action action) {
        final Map<String, String> dimensions = new HashMap<>();
        dimensions.put(Metrics.DIMENSION_KEY_ACTION_TYPE, action.name());
        dimensions.put(Metrics.DIMENSION_KEY_RESOURCE_TYPE, this.getResourceTypeName());

        publishMetric(
            Metrics.METRIC_NAME_HANDLER_INVOCATION_COUNT,
            dimensions,
            StandardUnit.Count,
            1.0,
            timestamp);
    }

    public void publishDurationMetric(final Date timestamp,
                                      final Action action,
                                      final long milliseconds) {
        final Map<String, String> dimensions = new HashMap<>();
        dimensions.put(Metrics.DIMENSION_KEY_ACTION_TYPE, action.name());
        dimensions.put(Metrics.DIMENSION_KEY_RESOURCE_TYPE, this.getResourceTypeName());

        publishMetric(
            Metrics.METRIC_NAME_HANDLER_DURATION,
            dimensions,
            StandardUnit.Milliseconds,
            (double)milliseconds,
            timestamp);
    }

    private void publishMetric(final String metricName,
                               final Map<String, String> dimensionData,
                               final StandardUnit unit,
                               final Double value,
                               final Date timestamp) {

        final List<Dimension> dimensions = new ArrayList<>();
        for (final Map.Entry<String, String> kvp: dimensionData.entrySet()) {
            final Dimension dimension = new Dimension()
                .withName(kvp.getKey())
                .withValue(kvp.getValue());
            dimensions.add(dimension);
        }

        final MetricDatum metricDatum = new MetricDatum()
            .withMetricName(metricName)
            .withUnit(unit)
            .withValue(value)
            .withDimensions(dimensions)
            .withTimestamp(timestamp);

        final PutMetricDataRequest putMetricDataRequest = new PutMetricDataRequest()
            .withNamespace(String.format("%s/%s", Metrics.METRIC_NAMESPACE_ROOT, resourceNamespace))
            .withMetricData(metricDatum);

        amazonCloudWatch.putMetricData(putMetricDataRequest);
    }
}
