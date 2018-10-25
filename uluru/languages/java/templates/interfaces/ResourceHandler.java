package {{ packageName }}.interfaces;

import {{ packageName }}.interfaces.HandlerCallback;
import {{ packageName }}.messages.HandlerRequest;
import {{ packageName }}.messages.ProgressEvent;

public interface ResourceHandler<T> {
    ProgressEvent<T> handleRequest(final HandlerRequest<T> request);
}
