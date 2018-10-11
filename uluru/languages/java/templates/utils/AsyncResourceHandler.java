package {{ packageName }}.utils;

import {{ packageName }}.messages.HandlerRequest;
import {{ packageName }}.messages.ProgressEvent;
import {{ packageName }}.utils.HandlerCallback;

public interface AsyncResourceHandler<T> {
    ProgressEvent<T> handleRequest(final HandlerRequest<T> request, HandlerCallback<T> callback);
}
