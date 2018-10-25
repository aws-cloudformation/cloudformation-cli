package {{ packageName }}.interfaces;

import {{ packageName }}.messages.ProgressEvent;

public interface HandlerCallback<T> {
    void recordProgressEvent(final ProgressEvent<T> event);
}
