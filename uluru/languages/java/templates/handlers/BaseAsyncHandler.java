{#"""Generates an abstract asynchronous handler class.
    Necessary variables for generation:
		@operation (Update|Delete)
		@pojo_name (The name of the top level Java POJO)
"""#}
package {{ packageName }}.handlers;

import {{ packageName }}.messages.HandlerRequest;
import {{ packageName }}.messages.ProgressEvent;
import {{ packageName }}.models.{{ pojo_name }};
import {{ packageName }}.utils.HandlerCallback;
import {{ packageName }}.utils.AsyncResourceHandler;

public abstract class BaseAsync{{ operation }}Handler implements AsyncResourceHandler<{{ pojo_name }}> {
    public ProgressEvent<{{ pojo_name }}> handleRequest(final HandlerRequest<{{ pojo_name }}> request, final HandlerCallback<{{ pojo_name }}> callback) {
        return do{{ operation }}(request, callback);
    }

    public abstract ProgressEvent<{{ pojo_name }}> do{{ operation }}(final HandlerRequest<{{ pojo_name }}> request, final HandlerCallback<{{ pojo_name }}> callback);
}
