package {{ packageName }}.handlers;

import {{ packageName }}.messages.HandlerRequest;
import {{ packageName }}.messages.HandlerStatus;
import {{ packageName }}.messages.ProgressEvent;
import {{ packageName }}.models.{{ pojo_name }};
import {{ packageName }}.utils.ErrorCodeMapper;
import {{ packageName }}.utils.HandlerCallback;

/**
 * Note: if your handler can return synchronously, extend Base{{ operation }}Handler instead
 */
public class {{ operation }}Handler extends BaseAsync{{ operation }}Handler {
    @Override
    public ProgressEvent<{{ pojo_name }}> do{{ operation }}(HandlerRequest<{{ pojo_name }}> request, HandlerCallback<{{ pojo_name }}> callback) {
        try {
            /**
             * Custom implementation here
             */
            return new ProgressEvent<{{ pojo_name }}>(request)
                    //.withResource()
                    .withStatus(HandlerStatus.COMPLETE);
        } catch (Exception e) {
            return new ProgressEvent<{{ pojo_name }}>(request)
                    .withStatus(HandlerStatus.FAILED)
                    .withErrorMessage(e.getMessage())
                    .withErrorCode(ErrorCodeMapper.mapError(request, e));
        }
    }
}
