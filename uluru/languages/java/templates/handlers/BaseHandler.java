{#"""
    Generates an abstract synchronous handler class.
    Necessary variables for generation:
		@operation (Update|Delete)
		@pojo_name (The name of the top level Java POJO)
"""#}
package {{ packageName }}.handlers;

import {{ packageName }}.messages.HandlerRequest;
import {{ packageName }}.messages.ProgressEvent;
import {{ packageName }}.models.{{ pojo_name }};
import {{ packageName }}.utils.ResourceHandler;

public abstract class Base{{ operation }}Handler implements ResourceHandler<{{ pojo_name }}> {
    public ProgressEvent<{{ pojo_name }}> handleRequest(final HandlerRequest<{{ pojo_name }}> request) {
        return do{{ operation }}(request);
    }

    public abstract ProgressEvent<{{ pojo_name }}> do{{ operation }}(final HandlerRequest<{{ pojo_name }}> request);
}
