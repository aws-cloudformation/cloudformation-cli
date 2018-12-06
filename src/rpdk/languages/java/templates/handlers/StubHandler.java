{#"""
    Generates a stub implementation of a handler class.
    Necessary variables for generation:
		@operation (Create|Read|Update|Delete|List)
		@pojo_name (The name of the top level Java POJO)
"""#}
package {{ packageName }}.handlers;

import {{ packageName }}.messages.HandlerRequest;
import {{ packageName }}.messages.HandlerStatus;
import {{ packageName }}.messages.ProgressEvent;
import {{ packageName }}.models.{{ pojo_name }};

public class {{ operation }}Handler extends Base{{ operation }}Handler {

    @Override
    public ProgressEvent<{{ pojo_name }}> do{{ operation }}(final HandlerRequest<{{ pojo_name }}> request) {

        // TODO : put your code here
        return new ProgressEvent<{{ pojo_name }}>()
            .withStatus(HandlerStatus.COMPLETE);

    }
}
