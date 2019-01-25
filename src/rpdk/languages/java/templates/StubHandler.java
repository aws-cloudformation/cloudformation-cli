package {{ package_name }};

import com.aws.cfn.proxy.Logger;
import com.aws.cfn.proxy.ProgressEvent;
import com.aws.cfn.proxy.ProgressStatus;
import com.aws.cfn.proxy.ResourceHandlerRequest;
import org.json.JSONObject;

public class {{ operation }}Handler extends BaseHandler {

    @Override
    public ProgressEvent handleRequest(
        final ResourceHandlerRequest<{{ pojo_name }}> request,
        final JSONObject callbackContext,
        final Logger logger) {

        final ResourceModel model = request.getDesiredResourceState();

        // TODO : put your code here

        final ProgressEvent pe = new ProgressEvent();
        pe.setResourceModel(model);
        pe.setStatus(ProgressStatus.Complete);
        return pe;
    }
}
