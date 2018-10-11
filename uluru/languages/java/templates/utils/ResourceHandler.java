package {{ packageName }}.utils;

import {{ packageName }}.messages.HandlerRequest;
import {{ packageName }}.messages.ProgressEvent;
import {{ packageName }}.utils.HandlerCallback;

public interface ResourceHandler<T> {
    ProgressEvent<T> handleRequest(final HandlerRequest<T> request);
}
