import abc
import base64
import json
from dataclasses import dataclass
from typing import Optional, Tuple, Union

from datetime import datetime
from json import JSONEncoder

import cv2
import numpy as np


# todo: информация о позиционировании наклейки
@dataclass
class ValidationParams:
    sticker_design: np.ndarray
    sticker_center: Tuple[float, float]
    acc_size: Tuple[float, float]
    sticker_size: Tuple[float, float]
    sticker_rotation: float

    def to_dict(self):
        """Convert ValidationParams to a serializable dictionary matching C# DTO structure"""
        if self.sticker_design is not None:
            _, encoded_img = cv2.imencode('.png', self.sticker_design)
            image_bytes = base64.b64encode(encoded_img.tobytes()).decode('utf-8')
        else:
            image_bytes = None

        return {
            "Image": image_bytes,
            "StickerCenter": {
                "X": float(self.sticker_center[0]),
                "Y": float(self.sticker_center[1])
            },
            "AccSize": {
                "Width": float(self.acc_size[0]),
                "Height": float(self.acc_size[1])
            },
            "StickerSize": {
                "Width": float(self.sticker_size[0]),
                "Height": float(self.sticker_size[1])
            },
            "StickerRotation": float(self.sticker_rotation)
        }


@dataclass
class ValidationResults:
    sticker_present: bool
    sticker_matches_design: Optional[bool] = None
    sticker_image: Optional[bytes] = None
    timestamp: datetime = None
    seq_number: int = 0
    sticker_position: Optional[Tuple[float, float]] = None
    sticker_size: Optional[Tuple[float, float]] = None
    sticker_rotation: Optional[float] = None


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
