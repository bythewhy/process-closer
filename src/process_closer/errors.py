class ProcessCloserError(Exception):
    pass


class InvalidTargetError(ProcessCloserError):
    pass


class TaskSchedulerError(ProcessCloserError):
    pass
