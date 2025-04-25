import abc
import base64
import json
from dataclasses import dataclass

from datetime import datetime
from json import JSONEncoder

import cv2
import numpy as np


# todo: информация о позиционировании наклейки
@dataclass
class ValidationParams:
    sticker_design: np.ndarray
    center: tuple
    size: tuple
    rotation: float


@dataclass
class ValidationResults:
    sticker_present: bool
    sticker_matches_design: bool | None
    sticker_image: np.ndarray | None = None  # Captured sticker image
    sticker_position: tuple | None = None  # Center position
    sticker_size: tuple| None = None  # Width and height
    sticker_rotation: float | None = None


@dataclass
class DetectionContext:
    image: np.ndarray
    detected_at: datetime = datetime.now
    seq_number: int = 0
    shape: np.ndarray | None = None  # BW mask
    processed_image: np.ndarray | None = None  # Aligned and cropped image
    validation_results: ValidationResults | None = None


from enum import IntEnum


class StreamingMessageType(IntEnum):
    RAW = 1
    SHAPE = 2
    PROCESSED = 3
    VALIDATION = 4

class StreamingMessageContent(abc.ABC):
    pass

class DefaultJsonEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__

class ImageStreamingMessageContent(StreamingMessageContent):
    def __init__(self, image: np.ndarray) -> None:
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 75]
        _, encoded_img = cv2.imencode('.jpg', image, encode_params)
        self.image: str = base64.b64encode(encoded_img.tobytes()).decode('utf-8')

@dataclass
class ValidationStreamingMessageContent(StreamingMessageContent):
    validation_result: ValidationResults


class StreamingMessage:
    def __init__(self, type: StreamingMessageType, content: StreamingMessageContent) -> None:
        self.type = type
        self.content = json.dumps(content, cls=DefaultJsonEncoder)
