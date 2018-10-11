package {{ packageName }}.messages;

public class RequestContext {
    private final String resourceType;
    private final Operation operation;
    private final String resourceTypeVersion;
    private final String clientRequestToken;
    private final String nextToken;
    private final AwsContext awsContext;

    public RequestContext(final String resourceType,
                          final Operation operation,
                          final String resourceTypeVersion,
                          final String clientRequestToken,
                          final String nextToken,
                          final AwsContext awsContext){
        this.resourceType = resourceType;
        this.operation = operation;
        this.resourceTypeVersion = resourceTypeVersion;
        this.clientRequestToken = clientRequestToken;
        this.nextToken = nextToken;
        this.awsContext = awsContext;
    }

    public String getResourceType() {
        return resourceType;
    }

    public Operation getOperation() {
        return operation;
    }

    public String getResourceTypeVersion() {
        return resourceTypeVersion;
    }

    public String getClientRequestToken() {
        return clientRequestToken;
    }

    public String getNextToken() {
        return nextToken;
    }

    public AwsContext getAwsContext() {
        return awsContext;
    }
}
