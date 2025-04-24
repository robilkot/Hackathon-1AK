
from enum import IntEnum

class StreamType(IntEnum):
    RAW = 1
    SHAPE = 2
    PROCESSED = 3
    VALIDATION = 4
    EVENTS = 5