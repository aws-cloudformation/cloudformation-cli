package {{ PackageNamePrefix }}.utils;

import com.amazon.cloudformation.selfservice.messages.Credentials;
import com.amazon.cloudformation.selfservice.messages.ResourceRequest;
import com.amazonaws.auth.AWSStaticCredentialsProvider;
import com.amazonaws.auth.BasicSessionCredentials;

import {{ Client.Builder }};
import {{ Client.Client }};

/*
    Provides a standardized class for handlers to retrieve clients.
 */
public class {{ Type|resource_type_service }}ClientBuilder {

    public static {{ Client.Client|java_class_name }} getClient(ResourceRequest input) {

        final Credentials credentials = input.getRequestData().getCredentials();

        return {{ Client.Builder|java_class_name }}.standard()
               .withRegion(input.getRegion())
               .withCredentials(
                    new AWSStaticCredentialsProvider(
                        new BasicSessionCredentials(credentials.getAccessKeyId(),
                                                    credentials.getSecretAccessKey(),
                                                    credentials.getSessionToken()))
               )
                .build();
    }
}
