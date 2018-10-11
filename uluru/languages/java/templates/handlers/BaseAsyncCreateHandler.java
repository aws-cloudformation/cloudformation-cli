{#"""Generates an abstract asynchronous create handler class.
    Necessary variables for generation:
		@pojo_name (The name of the top level Java POJO)
    """
#}
package {{ packageName }}.handlers;

import {{ packageName }}.messages.HandlerRequest;
import {{ packageName }}.messages.ProgressEvent;
import {{ packageName }}.models.{{ pojo_name }};
import {{ packageName }}.utils.HandlerCallback;
import {{ packageName }}.utils.AsyncResourceHandler;

public abstract class BaseAsyncCreateHandler implements AsyncResourceHandler<{{ pojo_name }}> {
    public ProgressEvent<{{ pojo_name }}> handleRequest(final HandlerRequest<{{ pojo_name }}> request, final HandlerCallback<{{ pojo_name }}> callback) {
        callback.recordProgressEvent(doCreate(request, callback));
        return doPostCreate(request, callback);
    }

    public abstract ProgressEvent<{{ pojo_name }}> doCreate(final HandlerRequest<{{ pojo_name }}> request, final HandlerCallback<{{ pojo_name }}> callback);

    public abstract ProgressEvent<{{ pojo_name }}> doPostCreate(final HandlerRequest<{{ pojo_name }}> request, final HandlerCallback<{{ pojo_name }}> callback);
}
