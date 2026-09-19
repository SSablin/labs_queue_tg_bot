from enum import Enum, IntEnum


class WorksheetIndex(IntEnum):
    QUEUE = 0
    SORT = 1
    CHEATS = 2


class QueueColumn(IntEnum):
    NAME = 1
    DATE = 2
    TIME = 3
    LAB = 4
    WAS = 5
    RECORD_ID = 6


class QueueStatus(str, Enum):
    ACTIVE = "no"
    DONE = "done"
    MISSED = "missed"
