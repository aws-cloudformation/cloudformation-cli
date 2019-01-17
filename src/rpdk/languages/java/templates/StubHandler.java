package {{ package_name }};

import com.aws.cfn.proxy.ProgressStatus;
import com.aws.cfn.proxy.HandlerRequest;
import com.aws.cfn.proxy.ProgressEvent;
import com.aws.cfn.proxy.RequestContext;

public class {{ operation }}Handler extends BaseHandler {

    @Override
    public ProgressEvent handleRequest(
        final HandlerRequest<{{ pojo_name }}> request,
        final RequestContext context) {

        final ResourceModel model = request.getResourceModel();

        // TODO : put your code here

        final ProgressEvent pe = new ProgressEvent();
        pe.setResourceModel(model);
        pe.setStatus(ProgressStatus.Complete);
        return pe;
    }
}
