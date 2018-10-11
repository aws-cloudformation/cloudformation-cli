package {{ packageName }}.handlers;

import java.io.Serializable;
/**
 * This is a sample ProgressMetadata file which should be customized for your service
 */
public class ProgressMetadata implements Serializable {
    private final String status;
    private final String api;
    private final String requestId;
    
    public ProgressMetadata(final String status, final String api, final String requestId) {
        this.status = status;
        this.api = api;
        this.requestId = requestId;
    }

    public String getStatus() {
        return status;
    }

    public String getApi() {
        return api;
    }

    public String getRequestId() {
        return requestId;
    }
}
