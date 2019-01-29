// This is a generated file. Modifications will be overwritten.
package {{ package_name }};

import com.aws.cfn.Action;
import com.aws.cfn.LambdaWrapper;
import com.aws.cfn.metrics.MetricsPublisher;
import com.aws.cfn.proxy.CallbackAdapter;
import com.aws.cfn.proxy.HandlerRequest;
import com.aws.cfn.proxy.LoggerProxy;
import com.aws.cfn.proxy.ProgressEvent;
import com.aws.cfn.proxy.RequestContext;
import com.aws.cfn.proxy.ResourceHandlerRequest;
import com.aws.cfn.resource.SchemaValidator;
import com.aws.cfn.resource.Serializer;
import com.aws.cfn.scheduler.CloudWatchScheduler;
import com.google.inject.Inject;
import org.json.JSONObject;

import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;

public final class HandlerWrapper extends LambdaWrapper<{{ pojo_name }}> {

    private final Configuration configuration = new Configuration();
    private final Map<Action, BaseHandler> handlers = new HashMap<>();

    public HandlerWrapper() {
        initialiseHandlers();
    }

    @Inject
    public HandlerWrapper(CallbackAdapter callbackAdapter,
                          MetricsPublisher metricsPublisher,
                          CloudWatchScheduler scheduler,
                          SchemaValidator validator,
                          Serializer serializer) {
        super(callbackAdapter, metricsPublisher, scheduler, validator, serializer);
        initialiseHandlers();
    }

    private void initialiseHandlers() {
{% for op in operations %}
        handlers.put(Action.{{ op }}, new {{ op }}Handler());
{% endfor %}
    }

    @Override
    public ProgressEvent invokeHandler(final ResourceHandlerRequest<{{ pojo_name }}> request,
                                       final Action action,
                                       final JSONObject callbackContext) {

        final String actionName = (action == null) ? "<null>" : action.toString(); // paranoia
        if (!handlers.containsKey(action))
            throw new RuntimeException("Unknown action " + actionName);

        final LoggerProxy loggerProxy = new LoggerProxy(this.logger);

        final BaseHandler handler = handlers.get(action);

        return handler.handleRequest(request, callbackContext, loggerProxy);
    }

    @Override
    public InputStream provideResourceSchema() {
        return this.configuration.resourceSchema();
    }

    @Override
    protected ResourceHandlerRequest<{{ pojo_name }}> transform(final HandlerRequest request) throws IOException {
        final {{ pojo_name }} desiredResourceState;
        final {{ pojo_name }} previousResourceState;

        if (request != null &&
            request.getRequestData() != null &&
            request.getRequestData().getResourceProperties() != null) {
            desiredResourceState = this.serializer.deserialize(
                request.getRequestData().getResourceProperties(),
                {{ pojo_name }}.class);
        } else {
            desiredResourceState = null;
        }

        if (request != null &&
            request.getRequestData() != null &&
            request.getRequestData().getPreviousResourceProperties() != null) {
            previousResourceState = this.serializer.deserialize(
                request.getRequestData().getPreviousResourceProperties(),
                {{ pojo_name }}.class);
        } else {
            previousResourceState = null;
        }

        return new ResourceHandlerRequest<>(
            request.getAwsAccountId(),
            request.getRegion(),
            request.getNextToken(),
            request.getResourceType(),
            request.getResourceTypeVersion(),
            request.getRequestData().getCredentials(),
            desiredResourceState,
            previousResourceState
        );
    }
}
