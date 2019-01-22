package com.aws.cfn.resource;

import org.apache.commons.lang3.RandomStringUtils;

import java.util.Random;

public class IdentifierUtils {

    /**
     * For named resources, use this method to safely generate a user friendly resource name
     * when the customer does not pass in an explicit name
     * For more info, see the named resources section of the developer guide
     * https://...
     * @return generated ID string
     */
    public static String generateResourceIdentifier(final String logicalResourceId,
                                                    final String clientRequestToken) {
        return generateResourceIdentifier(logicalResourceId,
            clientRequestToken,
            Constants.GENERATED_PHYSICALID_MAXLEN);
    }

    /**
     * For named resources, use this method to safely generate a user friendly resource name
     * when the customer does not pass in an explicit name
     * For more info, see the named resources section of the developer guide
     * https://...
     * @return generated ID string
     */
    public static String generateResourceIdentifier(final String logicalResourceId,
                                                    final String clientRequestToken,
                                                    final int maxLength) {
        final int maxLogicalIdLength = maxLength - (Constants.GUID_LENGTH + 1);

        final int endIndex = logicalResourceId.length() > maxLogicalIdLength
            ? maxLogicalIdLength
            : logicalResourceId.length();

        final StringBuilder sb = new StringBuilder();
        if (endIndex > 0) {
            sb.append(logicalResourceId.substring(0, endIndex)).append("-");
        }

        return sb.append(RandomStringUtils.random(Constants.GUID_LENGTH,
            0,
            0,
            true,
            true,
            null,
            new Random(clientRequestToken.hashCode()))).toString();
    }
}
