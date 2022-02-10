from enum import Enum, auto


class AutoName(Enum):
    @staticmethod
    def _generate_next_value_(name, _start, _count, _last_values):
        return name


class Action(str, AutoName):
    CREATE = auto()
    READ = auto()
    UPDATE = auto()
    DELETE = auto()
    LIST = auto()


class OperationStatus(AutoName):
    PENDING = auto()
    IN_PROGRESS = auto()
    SUCCESS = auto()
    FAILED = auto()


class HookInvocationPoint(str, AutoName):
    CREATE_PRE_PROVISION = auto()
    UPDATE_PRE_PROVISION = auto()
    DELETE_PRE_PROVISION = auto()


class HookStatus(AutoName):
    IN_PROGRESS = auto()
    SUCCESS = auto()
    FAILED = auto()


# pylint: disable=invalid-name
class HandlerErrorCode(AutoName):
    NotUpdatable = auto()
    InvalidRequest = auto()
    AccessDenied = auto()
    InvalidCredentials = auto()
    AlreadyExists = auto()
    NotFound = auto()
    ResourceConflict = auto()
    Throttling = auto()
    ServiceLimitExceeded = auto()
    NotStabilized = auto()
    GeneralServiceException = auto()
    ServiceInternalError = auto()
    NetworkFailure = auto()
    InternalFailure = auto()
    InvalidTypeConfiguration = auto()
    HandlerInternalFailure = auto()
    NonCompliant = auto()
    Unknown = auto()
