// This is a generated file. Modifications will be overwritten.
package {{ package_name }};

import com.aws.cfn.Action;
import com.aws.cfn.LambdaWrapper;
import com.aws.rpdk.HandlerRequest;
import com.aws.rpdk.ProgressEvent;
import com.aws.rpdk.RequestContext;

import {{ package_name }}.{{ pojo_name }};

public final class HandlerWrapper extends LambdaWrapper<{{ pojo_name }}> {

    private final Map<Action, BaseHandler> handlers = new HashMap<>();

    public HandlerWrapper() {

        {{ client_package_name }} client = {{ client_builder }}.defaultClient();

{% for op in operations %}
        handlers.put({{ op }}, new {{ op }}Handler(client));
{% endfor %}
    }

    @Override
    public ProgressEvent invokeHandler(final HandlerRequest<{{ pojo_name }}> request,
                                       final Action action,
                                       final RequestContext context) {

        final String actionName = (action == null) ? "<null>" : action.toString(); // paranoia
        if (!handlers.containsKey(action))
            throw new RuntimeException("Unknown action " + actionName);

        handlers.get(action).handlerRequest(request, context);
    }
}
