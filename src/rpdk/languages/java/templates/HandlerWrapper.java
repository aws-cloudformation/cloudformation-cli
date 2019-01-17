// This is a generated file. Modifications will be overwritten.
package {{ package_name }};

import com.aws.cfn.Action;
import com.aws.cfn.LambdaWrapper;
import com.aws.cfn.proxy.HandlerRequest;
import com.aws.cfn.proxy.ProgressEvent;
import com.aws.cfn.proxy.RequestContext;

import {{ package_name }}.{{ pojo_name }};

import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;

public final class HandlerWrapper extends LambdaWrapper<{{ pojo_name }}> {

    private final Configuration configuration = new Configuration();
    private final Map<Action, BaseHandler> handlers = new HashMap<>();

    public HandlerWrapper() {
{% for op in operations %}
        handlers.put(Action.{{ op }}, new {{ op }}Handler());
{% endfor %}
    }

    @Override
    public ProgressEvent invokeHandler(final HandlerRequest<{{ pojo_name }}> request,
                                       final Action action,
                                       final RequestContext context) {

        final String actionName = (action == null) ? "<null>" : action.toString(); // paranoia
        if (!handlers.containsKey(action))
            throw new RuntimeException("Unknown action " + actionName);

        {{ aws_sdk_client_type_name }} client = AWSSDKClientFactory.newClient(
            request.getRequestData().getCredentials().getAccessKeyId(),
            request.getRequestData().getCredentials().getSecretAccessKey(),
            request.getRequestData().getRegion()
        );

        final BaseHandler handler = handlers.get(action);
        handler.setClient(client);

        return handler.handleRequest(request, context);
    }

    @Override
    public InputStream provideResourceSchema() {
        return this.configuration.resourceSchema();
    }
}
