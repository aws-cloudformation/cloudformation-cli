package {{ packageName }}.handlers;

import {{ packageName }}.messages.HandlerRequest;
import {{ packageName }}.messages.HandlerStatus;
import {{ packageName }}.messages.ProgressEvent;
import {{ packageName }}.models.{{ pojo_name }};
import {{ packageName }}.utils.ErrorCodeMapper;
import {{ packageName }}.utils.HandlerCallback;
import {{ packageName }}.utils.ProgressMetadata;

/**
 * Note: if your handler can return synchronously, extend BaseCreateHandler instead
 */
public class CreateHandler extends BaseAsyncCreateHandler {
    @Override
    public ProgressEvent<{{ pojo_name }}> doCreate(final HandlerRequest<{{ pojo_name }}> request, final HandlerCallback<{{ pojo_name }}> callback) {
        try {
            /**
             * Custom implementation here
             */
            return new ProgressEvent<{{ pojo_name }}>(request)
                    // .withResource()
                    .withStatus(HandlerStatus.IN_PROGRESS);
        } catch (Exception e) {
            return new ProgressEvent<{{ pojo_name }}>(request)
                    .withStatus(HandlerStatus.FAILED)
                    .withErrorMessage(e.getMessage())
                    .withErrorCode(ErrorCodeMapper.mapError(request, e));
        }
    }

    @Override
    public ProgressEvent<{{ pojo_name }}> doPostCreate(final HandlerRequest<{{ pojo_name }}> request, final HandlerCallback<{{ pojo_name }}> callback) {
        try {
            /**
             * Custom implementation here
             */
            callback.recordProgressEvent(new ProgressEvent<{{ pojo_name }}>(request)
                    .withProgressMetadata(new ProgressMetadata("creating", "addThing", "abcd-1234"))
                    .withStatus(HandlerStatus.IN_PROGRESS));

            return new ProgressEvent<{{ pojo_name }}>(request)
                    // .withResource()
                    .withStatus(HandlerStatus.COMPLETE);
        } catch (Exception e) {
            return new ProgressEvent<{{ pojo_name }}>(request)
                    .withStatus(HandlerStatus.FAILED)
                    .withErrorMessage(e.getMessage())
                    .withErrorCode(ErrorCodeMapper.mapError(request, e));
        }

    }
}
