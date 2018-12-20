// This is a generated file. Modifications will be overwritten.
package {{ package_name }};

import com.aws.rpdk.HandlerRequest;
import com.aws.rpdk.ProgressEvent;
import com.aws.rpdk.RequestContext;

public abstract class BaseHandler {

    protected final {{ aws_sdk_client_type_name }} client;

    public BaseHandler({{ aws_sdk_client_type_name }} client) {
        this.client = client;
    }

    public abstract ProgressEvent handleRequest(
        final HandlerRequest<{{ pojo_name }}> request,
        final RequestContext context);

}
