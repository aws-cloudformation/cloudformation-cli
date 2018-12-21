// This is a generated file. Modifications will be overwritten.
package {{ package_name }};

import com.amazonaws.auth.AWSCredentials;
import com.amazonaws.auth.AWSStaticCredentialsProvider;
import com.amazonaws.auth.BasicAWSCredentials;

public class AWSSDKClientFactory {

    public static {{ aws_sdk_client_type_name }} newClient(
        final String accessKey,
        final String secretKey,
        final String region) {

        final AWSCredentials credentials = new BasicAWSCredentials(accessKey, secretKey);
        final {{ aws_sdk_client_type_name }} client = {{ aws_sdk_client_type_name }}ClientBuilder.standard()
            .withCredentials(new AWSStaticCredentialsProvider(credentials))
            .withRegion(region)
            .build();

        return client;
    }

}
