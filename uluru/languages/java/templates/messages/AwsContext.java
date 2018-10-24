package {{ packageName }}.messages;

import sun.security.krb5.Credentials;

public class AwsContext {
    private final String accountId;
    private final String region;
    private final Credentials credentials;

    public AwsContext(final String accountId,
                      final String region,
                      final Credentials credentials) {
        this.accountId = accountId;
        this.region = region;
        this.credentials = credentials;
    }

    public String getAccountId() {
        return accountId;
    }

    public String getRegion() {
        return region;
    }

    public Credentials getCredentials() {
        return credentials;
    }
}
