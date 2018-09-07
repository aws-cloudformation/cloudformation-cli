{# Integration tests to test that the handlers work as CFN expects #}
{% set resource_name = Type|resource_type_resource -%}
{% set resource_variable = "requestResource" -%}

package integration;

import com.amazon.cloudformation.selfservice.messages.ResourceRequest;
import {{ packageNamePrefix }}.handlers.*;
import {{ packageNamePrefix }}.models.{{ resource_name }}Model;
import {{ packageNamePrefix }}.utils.{{ Type|resource_type_service }}ClientBuilder;

import {{ Client.Client }};
import {{ Client.ResourceModel }}.*;

import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.*;

import java.util.concurrent.TimeUnit;

/*
    This class is used to fully test API calls.
    This current iteration runs based on the credentials found by the AWS cli.
 */
public class {{ resource_name }}IntegrationTests {

    /*
        Outline. More exception handling will need to be added.
     */

    private {{ Client.Client|java_class_name }} client = {{ Type|resource_type_service }}ClientBuilder.getClient(new ResourceRequest());
    //NOTE: "new ResourceRequest()" is kinda hacky. Thoughts??

    private {{ resource_name }}Model {{ resource_variable }};

    /** PROVIDER CODE HERE -- PLEASE ADD CONSTANTS & VALUES FOR RESOURCE PROPERTIES (sample provided) **/
    {% for property_name, property_details in Properties.items() %}
    {% set property_type = property_details.Type|property_type_json_to_java %}
    protected static final {{ property_type }} {{ property_name|upper }} = "SAMPLE";
    {% endfor %}

    /** END PROVIDER CODE **/

    protected ResourceRequest context;
    protected static final String TOKEN = "token";

    private {{ resource_name }}CreateHandler createHandler = new {{ resource_name }}CreateHandler();
    private {{ resource_name }}DeleteHandler deleteHandler = new {{ resource_name }}DeleteHandler();
    private {{ resource_name }}UpdateHandler updateHandler = new {{ resource_name }}UpdateHandler();
    private {{ resource_name }}ReadHandler readHandler = new {{ resource_name }}ReadHandler();
    private {{ resource_name }}ListHandler listHandler = new {{ resource_name }}ListHandler();

    private final long TIMEOUT_SECONDS = 120;

    @Before
    public void setup() {
        /** PROVIDER CODE HERE -- PLEASE ADD PROPERTIES TO MODEL (sample provided) **/
        {{ resource_variable }} = new {{ resource_name }}Model()
        {% for property_name, property_details in Properties.items()%}
            .with{{ property_name }}({{ property_name|upper }}){% if loop.last %};{% endif %}

        {% endfor %}
		/** END PROVIDER CODE **/

        context = new ResourceRequest();
        context.setClientRequestToken(TOKEN);
    }

    private void assertResourceCreateCompletes() {
        /** PROVIDER CODE NECESSARY TO DESCRIBE FINAL RESOURCE AS resourceDescription
        Sample provided with required properties. **/
        ResourceDescription resourceDescription;

        {% for property_name, property_details in Properties.items() if property_details.Required %}
        assertEquals({{ property_name|upper }}, resourceDescription.get{{ property_name }}());
        {% endfor %}
        /** END PROVIDER CODE **/
    }

    @Test
    public void testResourceCreate() {
        createHandler.handleExecute({{ resource_variable }}, client, context);
        stabilize({{ resource_variable }}, client, TIMEOUT_SECONDS);
        assertResourceCreateCompletes();
        testResourceDeleteCompletes();
    }

    @Test(expected = ResourceNotFoundException.class)
    public void testResourceDeleteCompletes() {
        deleteHandler.handleExecute({{ resource_variable }}, client, context);
        client.describeStream(NAME);
    }

    //TODO later
    @Test
    public void testResourceUpdate() {
        updateHandler.handleExecute({{ resource_variable }}, client, context);
    }

    @Test
    public void testCreateAlreadyExists() {

    }

    @Test
    public void testCreateWithSameClientRequestToken() {

    }

    @Test
    public void testUpdateThenRollback() {

    }

    @Test
    public void testMultipleRequests() {
    	//i.e. create, then update, then delete.
    }

    private void stabilize({{ resource_name }}Model {{ resource_name|lower }}, {{ Client.Client|java_class_name }} client, long timeout) {
        final long timeoutInMillis = TimeUnit.SECONDS.toMillis(timeout);
        final long start = System.currentTimeMillis();

        /** PROVIDER CODE HERE FOR STATUS CHECK **/
        while (!client."DESCRIBE_STATUS"
                .equals("ACTIVE")) {
            if (System.currentTimeMillis() - start > timeoutInMillis)
                throw new RuntimeException("Timed out waiting for Active status on Stream: " + stream.getName());
            try {
                Thread.sleep(5000);
            } catch (Exception e) {
                System.err.println(e.getMessage());
            }
        }
    }

}
