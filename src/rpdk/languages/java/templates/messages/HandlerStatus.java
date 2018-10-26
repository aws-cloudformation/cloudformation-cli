package {{ packageName }}.messages;

/**
 * The status of the handler at the time of the progress event.
 * IN_PROGRESS MUST only be used for asynchronous calls
 */
public enum HandlerStatus {
    IN_PROGRESS,
    FAILED,
    COMPLETE
}
