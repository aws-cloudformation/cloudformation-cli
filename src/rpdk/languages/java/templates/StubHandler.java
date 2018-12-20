package {{ package_name }};

import com.aws.cfn.ProgressStatus;
import com.aws.rpdk.HandlerRequest;
import com.aws.rpdk.ProgressEvent;
import com.aws.rpdk.RequestContext;

public class {{ operation }}Handler extends BaseHandler {

    public {{ operation }}Handler({{ client_package_name }} client) {
        super(client);
    }

    public static ProgressEvent handle{{ operation }}(
        final HandlerRequest<{{ pojo_name }}> request,
        final RequestContext context) {

        // TODO : put your code here
        return new ProgressEvent(ProgressStatus.Complete, "");
    }
}
