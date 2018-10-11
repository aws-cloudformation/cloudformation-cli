package {{ packageName }}.messages;

import org.apache.commons.lang.builder.EqualsBuilder;
import org.apache.commons.lang.builder.HashCodeBuilder;
import org.apache.commons.lang.builder.ToStringBuilder;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;

public class ProgressEvent<T> implements Serializable {
    private String clientRequestToken;
    private String resourceType;
    private List<T> resources;
    private Object progressMetadata;
    private HandlerStatus status;
    private ErrorCode errorCode;
    private String errorMessage;
    private String nextToken;

    public ProgressEvent(){}

    public ProgressEvent(final HandlerRequest request) {
        this.clientRequestToken = request.getRequestContext().getClientRequestToken();
        this.resourceType = request.getRequestContext().getResourceType();
    }

    public String getClientRequestToken() {
        return clientRequestToken;
    }

    public String getResourceType() {
        return resourceType;
    }

    public List<T> getResources() {
        return resources;
    }

    public Object getProgressMetadata() {
        return progressMetadata;
    }

    public HandlerStatus getStatus() {
        return status;
    }

    public ErrorCode getErrorCode() {
        return errorCode;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public String getNextToken() {
        return nextToken;
    }

    public ProgressEvent<T> withClientRequestToken(final String clientRequestToken){
        this.clientRequestToken = clientRequestToken;
        return this;
    }
    public ProgressEvent<T> withResourceType(final String resourceType){
        this.resourceType = resourceType;
        return this;
    }

    public ProgressEvent<T> withResources(final List<T> resources) {
        this.resources = resources
        return this;
    }

    public ProgressEvent<T> withResource(final T resource) {
        this.resources = new ArrayList<T>(){%raw%}{{
            add(resource);
        }};{%endraw%}
        return this;
    }

    public ProgressEvent<T> withProgressMetadata(Object progressMetadata) {
        this.progressMetadata = progressMetadata;
        return this;
    }

    public ProgressEvent<T> withStatus(final HandlerStatus status){
        this.status = status;
        return this;
    }
    public ProgressEvent<T> withErrorCode(final ErrorCode errorCode){
        this.errorCode = errorCode;
        return this;
    }
    public ProgressEvent<T> withErrorMessage(final String errorMessage){
        this.errorMessage = errorMessage;
        return this;
    }

    public ProgressEvent<T> withNextToken(final String nextToken){
        this.nextToken = nextToken;
        return this;
    }

    @Override
    public String toString() {
        return new ToStringBuilder(this)
                .append("ClientRequestToken", clientRequestToken)
                .append("ResourceType", resourceType)
                .append("Resources", resources)
                .append("ProgressMetadata", progressMetadata)
                .append("Status", status)
                .append("ErrorCode", errorCode)
                .append("ErrorMessage", errorMessage)
                .append("NextToken", nextToken)
                .toString();
    }

    @Override
    public int hashCode() {
        return new HashCodeBuilder()
                .append(clientRequestToken)
                .append(resourceType)
                .append(resources)
                .append(progressMetadata)
                .append(status)
                .append(errorCode)
                .append(errorMessage)
                .append(nextToken)
                .toHashCode();
    }

    @Override
    public boolean equals(Object rhs) {
        if (rhs == null) return false;
        if (this == rhs) return true;
        if (rhs.getClass() != ProgressEvent.class) return false;
        final ProgressEvent<T> other = (ProgressEvent<T>) rhs;
        return new EqualsBuilder()
                .append(clientRequestToken, other.clientRequestToken)
                .append(resourceType, other.resourceType)
                .append(resources, other.resources)
                .append(progressMetadata, other.progressMetadata)
                .append(status, other.status)
                .append(errorCode, other.errorCode)
                .append(errorMessage, other.errorMessage)
                .append(nextToken, other.nextToken)
                .isEquals();
    }
}
