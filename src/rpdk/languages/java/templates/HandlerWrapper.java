// This is a generated file. Modifications will be overwritten.
package {{ package_name }};

import com.aws.cfn.Action;
import com.aws.cfn.LambdaWrapper;
import com.aws.rpdk.HandlerRequest;
import com.aws.rpdk.ProgressEvent;
import com.aws.rpdk.RequestContext;

import {{ package_name }}.{{ pojo_name }};

public final class HandlerWrapper extends LambdaWrapper<{{ pojo_name }}> {

    @Override
    public ProgressEvent invokeHandler(final HandlerRequest<{{ pojo_name }}> request,
                                       final Action action,
                                       final RequestContext context) {

        switch (action) {
{% for op in operations %}
            case {{ op }}:
                return {{ op }}Handler.handle{{ op }}(request, context);
{% endfor %}
        }

        final String actionName = (action == null) ? "<null>" : action.toString(); // paranoia
        throw new RuntimeException("Unknown action " + actionName);
    }
}
