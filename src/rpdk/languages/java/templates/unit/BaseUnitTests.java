{#
    Necessary subtemplate-specific variables:
    handler_type (name of handler)
    subhandler (object with the handler's properties)
#}
{% set resource_name = Type|resource_type_resource %}
{% set handler_variable = handler_type|lower ~ 'Handler' %}
package unit;

import com.amazon.cloudformation.selfservice.messages.ResourceRequest;
import com.amazon.cloudformation.selfservice.messages.ResourceResponse;
import com.amazon.cloudformation.selfservice.messages.Status;
import com.amazonaws.services.kms.model.AlreadyExistsException;
import {{ packageNamePrefix }}.handlers.{{ resource_name }}{{ handler_type }}Handler;
import {{ packageNamePrefix }}.models.{{ resource_name }}Model;

import org.junit.After;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.Mock;
import org.mockito.junit.MockitoJUnitRunner;

import {{ Client.ResourceModel }}.*;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verifyNoMoreInteractions;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;


@RunWith(MockitoJUnitRunner.class)
public class {{ handler_type }}HandlerUnitTests extends TestBase {

    {% block extra_definitions %}{% endblock %}

    {% if subhandler.ApiCalls %}
    {% for call in subhandler.ApiCalls %}
        {% if call.Exceptions %}
    /** PROVIDER MAY WRITE CUSTOM EXCEPTION MESSAGES FOR {{ call.Name|upper }} **/
        {% for exception in call.Exceptions %}
    protected static final {{ exception.Name }} {{ exception.Name|lowercase_first_letter }} = new {{ exception.Name }}("custom message");
        {% endfor %}
    /** END CUSTOM MESSAGES **/
        {% endif %}
    {% endfor %}
    {% endif %}

    private {{ resource_name }}{{ handler_type }}Handler {{ handler_variable }} = new {{ resource_name }}{{ handler_type }}Handler();

    private void verify{{ handler_type }}Call() {
        /** PROVIDER CODE HERE FOR THE CALLS.
        Sample starter code provided here. **/
        {% if subhandler.ApiCalls %}
        verify(client).{{ subhandler.ApiCalls[0].Name }}();
        {% endif %}
        /** END PROVIDER CODE **/
    }

    //Can be run independently and expected to work in the happy path case.
    @Test
    public void testSuccess() {
        ResourceResponse response = {{ handler_variable }}.handleExecute(requestResource, client, context);
        verifyResponse(response, true, physicalResourceId, null, Status.SUCCESS);
        verify{{ handler_type }}Call();
    }

    //Only to be used in conjunction with other failure methods. Will not succeed if run independently.
    @Test
    public void testFailure() {
        ResourceResponse response = {{ handler_variable }}.handleExecute(requestResource, client, context);
        verifyResponse(response, false, physicalResourceId, null, Status.FAILURE);
        verify{{ handler_type }}Call();
    }

    @Test
    public void testRetry() {
        ResourceResponse response = {{ handler_variable }}.handleExecute(requestResource, client, context);
        verifyResponse(response, false, physicalResourceId, null, Status.RETRY);
        verify{{ handler_type }}Call();
    }

    {% block extra_tests %}{% endblock %} {# USE FOR SPECIFIC HANDLER TESTS %}

    {# exception tests #}
    /** PROVIDER CODE EDITS MAY BE NECESSARY **/
    {% if subhandler.ApiCalls %}
    {% for call in subhandler.ApiCalls %}
        {% if call.Exceptions %}
        {% for exception in call.Exceptions %}
    @Test
    public void test{{ exception.Name }}() {
        when(client.{{ call.Name }}()).thenThrow({{ exception.Name|lowercase_first_letter }});
        test{{ exception.Response }}();
    }

        {% endfor %}
        {% endif %}
    {% endfor %}
    {% endif %}
    /** END PROVIDER EDITS **/


    /** PLEASE FILL THE {{ handler_type|upper }} METHOD APPROPRIATELY FOR THE FOLLOWING **/

    //400 exceptions should fail.
    @Test
    public void test400() {
        when(client.{{ handler_type|upper }}()).thenThrow(exception400);
        ResourceResponse response = {{ handler_type|lower }}Handler.handleExecute(requestResource, client, context);
        verifyResponse(response, false, physicalResourceId, exception400.getMessage(), Status.FAILURE);
        verify{{ handler_type }}Call();
    }

    //500 exceptions should retry.
    @Test
    public void test500() {
        when(client.{{ handler_type|upper }}()).thenThrow(exception500);
        ResourceResponse response = {{ handler_type|lower }}Handler.handleExecute(requestResource, client, context);
        verifyResponse(response, false, physicalResourceId, exception500.getMessage(), Status.RETRY);
        verify{{ handler_type }}Call();
    }

    @Test
    public void testUnknownException() {
        when(client.{{ handler_type|upper }}()).thenThrow(unknownException);
        testFailure();
    }

    @After
    public void after() {
        verifyNoMoreInteractions(client);
    }
}
