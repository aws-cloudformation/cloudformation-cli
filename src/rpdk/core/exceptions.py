class RPDKBaseException(Exception):
    pass


class InternalError(RPDKBaseException):
    pass


class SpecValidationError(RPDKBaseException):
    pass


class WizardError(RPDKBaseException):
    pass


class WizardAbortError(WizardError):
    pass


class WizardValidationError(WizardError):
    pass


class InvalidSettingsError(RPDKBaseException):
    pass
