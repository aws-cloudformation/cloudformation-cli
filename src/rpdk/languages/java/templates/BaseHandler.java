// This is a generated file. Modifications will be overwritten.
package {{ package_name }};

import com.aws.cfn.proxy.HandlerRequest;
import com.aws.cfn.proxy.ProgressEvent;
import com.aws.cfn.proxy.RequestContext;

public abstract class BaseHandler {

    public abstract ProgressEvent handleRequest(
        final HandlerRequest<{{ pojo_name }}> request,
        final RequestContext context);

}
