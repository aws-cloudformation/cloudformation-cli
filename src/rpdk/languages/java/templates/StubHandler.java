package {{ package_name }};

import com.aws.cfn.ProgressStatus;
import com.aws.rpdk.HandlerRequest;
import com.aws.rpdk.ProgressEvent;
import com.aws.rpdk.RequestContext;

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
