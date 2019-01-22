package com.aws.cfn;

import com.aws.cfn.metrics.MetricsPublisher;
import com.aws.cfn.proxy.CallbackAdapter;
import com.aws.cfn.proxy.HandlerRequest;
import com.aws.cfn.proxy.ProgressEvent;
import com.aws.cfn.proxy.RequestContext;
import com.aws.cfn.resource.SchemaValidator;
import com.aws.cfn.scheduler.CloudWatchScheduler;
import com.google.inject.Inject;
import lombok.Data;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.Charset;

/**
 * Test class used for testing of LambdaWrapper functionality
 * @param <TestModel>
 */
@Data
public class WrapperOverride<TestModel> extends LambdaWrapper<TestModel> {

    /**
     * This .ctor provided for testing
     */
    @Inject
    public WrapperOverride(final CallbackAdapter callbackAdapter,
                           final MetricsPublisher metricsPublisher,
                           final CloudWatchScheduler scheduler,
                           final SchemaValidator validator) {
        super(callbackAdapter, metricsPublisher, scheduler, validator);
    }

    @Override
    public InputStream provideResourceSchema() {
        return new ByteArrayInputStream(
            "{ \"properties\": { \"propertyA\": { \"type\": \"string\" } }".getBytes(Charset.forName("UTF8")));
    }

    @Override
    public ProgressEvent<TestModel> invokeHandler(final HandlerRequest<TestModel> request,
                                                  final Action action,
                                                  final RequestContext context) {
        return invokeHandlerResponse;
    }


    public ProgressEvent<TestModel> invokeHandlerResponse;
}
