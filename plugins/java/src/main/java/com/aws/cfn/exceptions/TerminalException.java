package com.aws.cfn.exceptions;

public class TerminalException extends RuntimeException {

    private static final long serialVersionUID = -1646136434112354328L;

    public TerminalException(final Throwable cause) {
        super(null, cause);
    }

    public TerminalException(final String customerFacingErrorMessage) {
        super(customerFacingErrorMessage);
    }

    public TerminalException(final String customerFacingErrorMessage,
                             final Throwable cause) {
        super(customerFacingErrorMessage, cause);
    }
}
