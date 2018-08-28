{% set resource_name = Type|resource_type_resource %}
package unit;

import com.amazon.cloudformation.selfservice.messages.ResourceRequest;
import com.amazon.cloudformation.selfservice.messages.ResourceResponse;
import com.amazon.cloudformation.selfservice.messages.Status;
import com.amazonaws.AmazonServiceException;

import {{ PackageNamePrefix }}.models.{{ resource_name }}Model;

import {{ Client.ResourceModel }}.*;
import {{ Client.Client }};

import org.junit.Before;
import org.mockito.Mock;
import utils.{{ Type|resource_type_service }}ClientBuilder;

import static org.junit.Assert.assertEquals;

public class TestBase {

    //standard Amazon exceptions
    protected static final AmazonServiceException exception500 = new AmazonServiceException("Server error");
    protected static final AmazonServiceException exception400 = new AmazonServiceException("Client error");
    protected static final RuntimeException unknownException = new RuntimeException("Runtime error");

    @Mock
    protected {{ Client.Client|java_class_name }} client = {{ Type|resource_type_service }}ClientBuilder.getClient(new ResourceRequest());
    @Mock
    protected static ResourceRequest context = new ResourceRequest();
    protected static final String TOKEN = "token";

    /** PROVIDER CODE BELOW -- please make edits to values of generated required properties
    	 and add properties as necessary **/
    protected static final String NAME = "Name";
    protected static final String physicalResourceId = NAME;

    private {{ resource_name }}Model requestResource;
    /** PROVIDER CUSTOMIZATION **/
    {% for property_name, property_details in Properties.items() %}
    {% set property_type = property_details.Type|property_type_json_to_java %}
    protected static final {{ property_type }} {{ property_name|upper }} = "SAMPLE";
    {% endfor %}
    /** END PROVIDER CUSTOMIZATION **/

    @Before
    public void setup() throws Exception {
        /** PROVIDER CUSTOMIZATION **/
        requestResource = new {{ resource_name }}Model()
        {% for property_name, property_details in Properties.items()%}
            .with{{ property_name }}({{ property_name|upper }}){% if loop.last %};{% endif %}

        {% endfor %}
        /** END PROVIDER CUSTOMIZATION **/
    }

    static {
        context.setClientRequestToken(TOKEN);
        exception400.setStatusCode(400);
        exception500.setStatusCode(500);
    }

    protected void verifyResponse(final ResourceResponse resourceResponse,
                                    final Boolean modified,
                                    final String physicalResourceId,
                                    final String message,
                                    final Status status) {

        if (modified != null) {
            assertEquals(modified, resourceResponse.getModified());
        }

        if (physicalResourceId != null) {
            assertEquals(physicalResourceId, resourceResponse.getResponseData().getPhysicalResourceId());
        }

        if (message != null) {
            assertEquals(message, resourceResponse.getMessage());
        }

        if (status != null) {
            assertEquals(status, resourceResponse.getStatus());
        }
    }



}
