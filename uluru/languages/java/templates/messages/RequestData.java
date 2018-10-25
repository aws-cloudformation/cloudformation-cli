package {{ packageName }}.messages;

import java.util.List;
import java.util.Map;

public class RequestData<T> {
    final T resourceProperties;
    final T previousResourceProperties;
    final Map<String, Object> behaviorSpecification;

    public RequestData(final T resourceProperties,
                       final T previousResourceProperties,
                       final Map<String, Object> behaviorSpecification) {
        this.resourceProperties = resourceProperties;
        this.previousResourceProperties = previousResourceProperties;
        this.behaviorSpecification = behaviorSpecification;
    }

    public T getResourceProperties() {
        return resourceProperties;
    }

    public T getPreviousResourceProperties() {
        return previousResourceProperties;
    }

    public Map<String, Object> getBehaviorSpecification() {
        return behaviorSpecification;
    }
}
