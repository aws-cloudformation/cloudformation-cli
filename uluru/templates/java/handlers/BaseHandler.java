{#
    Necessary handler-specific variables:
    handler_type (name of handler)
    subhandler (object with the handler's properties)
#}
{% set resource_name = Type|resource_type_name -%}

package {{ PackageNamePrefix }}.handlers;

import com.amazon.cloudformation.selfservice.messages.ResourceRequest;
import com.amazon.cloudformation.selfservice.messages.ResourceResponse;
import {{ PackageNamePrefix }}.models.{{ resource_name }}Model;
import {{ PackageNamePrefix }}.utils.ResourceResponseReturner;
import {{ Client.ResourceModel }}.*;
import {{ Client.Client }};

/*
    This class contains a method that will {{ handler_type|lower }} a {{ resource_name }} resource using its API.
    Multiple calls may be necessary to fully execute this handler such that the resource is ready to be used by the customer upon completion.
    Any still-running processes can be handled during Stabilization, which can be implemented as an Aspect.
    Please include appropriate logic to catch any exceptions that may arise during execution, as specified in the handlers schema.
 */
public class {{ resource_name }}{{ handler_type }}Handler {

    public ResourceResponse handleExecute(final {{ resource_name }}Model {{ resource_name|lower }}, final {{ Client.Client|java_class_name }} client, final ResourceRequest context) {
        final String physicalResourceId = ""; //todo: how to make this specific?
        boolean modified = false;
        final String clientRequestToken = context.getClientRequestToken();
        try {

            try {
                /** PROVIDER CUSTOM IMPLEMENTATION HERE **/
                /*
                    Happy-path case
                */
                {% if subhandler.ApiCalls %}
                {% for call in subhandler.ApiCalls %}
                client.{{ call.Name }}(); //NEXT STEP: adding the parameters.

                {% endfor %}
                {% endif %}
                /** END PROVIDER CUSTOM CODE **/

                modified = true;
                return ResourceResponseReturner.handleSuccess(physicalResourceId, modified, clientRequestToken);

            } /** PROVIDER EXCEPTION CODE HERE **/
            {# NOTE: previous version of the schema had exceptions grouped by handler instead of ApiCall.
                Revert to that version (also helps with duplicate checking) if needed. #}
            {% if subhandler.ApiCalls %}
            {% for call in subhandler.ApiCalls %}
                {% if call.Exceptions %}
                {% for exception in call.Exceptions if exception.Response != 'Failure' %}
                    {% set exception_response = exception.Response %}
                    {% if exception_response == 'Success' %}
                        {% set modified = call.ActionType|modified_from_action_type %}
                {% else %}
                    {% set modified = 'false' %}
                {% endif %}
              catch ({{ exception.Name }} e) {
                return ResourceResponseReturner.handle{{ exception_response }}(physicalResourceId, {{ modified }}, clientRequestToken);
              }
                {% endfor %}
                {% endif %}
            {% endfor %}
            {% endif %}
            /** END PROVIDER CODE **/
        } catch (final Exception e) {
            return ResourceResponseReturner.handleDefaultError(e, physicalResourceId, false, clientRequestToken);
        }
    }
}
