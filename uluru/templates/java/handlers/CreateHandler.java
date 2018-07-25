package {{ package_name_prefix }}.handlers;

import com.amazon.cloudformation.selfservice.messages.ResourceRequest;
import com.amazon.cloudformation.selfservice.messages.ResourceResponse;
import {{ package_name_prefix }}.models.{{ Type|resource_type_name }}Model;
import {{ Client.Builder }};
import {{ Client.Client }};

public class CreateHandler extends CFNLambdaHandler<{{ Type|resource_type_name }}Model, {{ Client.Builder|java_class_name }}, {{ Client.Client|java_class_name }}> {

public ResourceResponse handleExecute(final {{ Client.Client|java_class_name }} client) {
    try {
        try {
            final String physicalResourceId = ""; //generate based on IdentifierPath
            final boolean modified = false;

            /** PROVIDER CUSTOM CODE HERE **/
            client.{{ Handlers.CreateHandler.ApiCall }}();

            modified = true;
            return super.handleSuccess(physicalResourceId, modified);

        } catch (final MyException e) {
            /** PROVIDER CUSTOM CODE HERE **/
            return super.handleDefaultError(e, physicalResourceId, modified);
        } catch (final Exception e) {
            return super.handleDefaultError(e, "physicalResourceId", false);
            //the handling of errors can also be put into a superclass of this class, etc.
            // in order to keep track of the client request tokens and input information.
        }
    }
}
