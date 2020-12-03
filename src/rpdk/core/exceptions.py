class RPDKBaseException(Exception):
    pass


class SysExitRecommendedError(RPDKBaseException):
    pass


class InternalError(RPDKBaseException):
    pass


class SpecValidationError(RPDKBaseException):
    pass


class FragmentValidationError(RPDKBaseException):
    pass


class WizardError(RPDKBaseException):
    pass


class WizardAbortError(WizardError):
    pass


class WizardValidationError(WizardError):
    pass


class UploadError(RPDKBaseException):
    pass


class InvalidProjectError(SysExitRecommendedError):
    pass


class CLIMisconfiguredError(SysExitRecommendedError):
    pass


class DownstreamError(RPDKBaseException):
    pass


class ContractTestError(RPDKBaseException):
    pass


class InvalidRequestError(ContractTestError):
    pass


class ModelResolverError(RPDKBaseException):
    pass


class InvalidFragmentFileError(RPDKBaseException):
    pass
