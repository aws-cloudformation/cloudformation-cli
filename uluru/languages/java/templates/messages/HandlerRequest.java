package {{ packageName }}.messages;

public class HandlerRequest<T> {
    private final RequestContext requestContext;
    private final RequestData<T> requestData;

    public HandlerRequest(final RequestContext requestContext, final RequestData requestData) {
        this.requestContext = requestContext;
        this.requestData = requestData;
    }

    public RequestContext getRequestContext() {
        return requestContext;
    }

    public RequestData<T> getRequestData() {
        return requestData;
    }
}
