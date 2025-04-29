import abc
import base64
import json
from dataclasses import dataclass
from typing import Optional, Tuple, Union

from datetime import datetime
from json import JSONEncoder

import cv2
import numpy as np


@dataclass
class StickerValidationParams:
    sticker_design: np.ndarray
    sticker_center: Tuple[float, float]
    acc_size: Tuple[float, float]
    sticker_size: Tuple[float, float]
    sticker_rotation: float

    def __str__(self):
        return f'center: {self.sticker_center}, size: {self.sticker_size}, rotation: {self.sticker_rotation}, acc_size: {self.acc_size}'

    def to_dict(self):
        """Convert ValidationParams to a serializable dictionary matching C# DTO structure"""
        _, encoded_img = cv2.imencode('.png', self.sticker_design)
        image_bytes = base64.b64encode(encoded_img.tobytes())

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

    @classmethod
    def from_dict(cls, params_dict: dict):
        # Decode base64 image
        image_bytes = base64.b64decode(params_dict["StickerDesign"])
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        # Extract coordinates and sizes
        sticker_center = (
            float(params_dict["StickerCenter"]["X"]),
            float(params_dict["StickerCenter"]["Y"])
        )

        acc_size = (
            float(params_dict["AccSize"]["Width"]),
            float(params_dict["AccSize"]["Height"])
        )

        sticker_size = (
            float(params_dict["StickerSize"]["Width"]),
            float(params_dict["StickerSize"]["Height"])
        )

        return cls(
            sticker_design=image,
            sticker_center=sticker_center,
            acc_size=acc_size,
            sticker_size=sticker_size,
            sticker_rotation=float(params_dict["StickerRotation"])
        )


@dataclass
class ValidationResults:
    sticker_present: bool
    sticker_matches_design: Optional[bool] = None
    sticker_image: np.ndarray | None = None
    sticker_position: Optional[Tuple[float, float]] = None
    sticker_size: Optional[Tuple[float, float]] = None
    sticker_rotation: Optional[float] = None
    seq_number: int = 0
    detected_at: datetime = datetime.now()

    def to_dict(self):
        """Convert to a format matching C# StickerValidationResultDTO"""
        image_bytes = None
        if self.sticker_image is not None:
            _, encoded_img = cv2.imencode('.png', self.sticker_image)
            image_bytes = base64.b64encode(encoded_img.tobytes()).decode('utf-8')

        timestamp = self.detected_at.isoformat() if isinstance(self.detected_at, datetime) else datetime.now().isoformat()
        sticker_position = None
        if self.sticker_position:
            sticker_position = {
                "X": float(self.sticker_position[0]),
                "Y": float(self.sticker_position[1])
            }

        sticker_size = None
        if self.sticker_size:
            sticker_size = {
                "Width": float(self.sticker_size[0]),
                "Height": float(self.sticker_size[1])
            }

        return {
            "Image": image_bytes,
            "Timestamp": timestamp,
            "SeqNumber": self.seq_number,
            "StickerPresent": self.sticker_present,
            "StickerMatchesDesign": self.sticker_matches_design,
            "StickerSize": sticker_size,
            "StickerPosition": sticker_position,
            "StickerRotation": float(self.sticker_rotation) if self.sticker_rotation is not None else None
        }

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
    @abc.abstractmethod
    def to_dict(self):
        """Convert to a serializable dictionary format"""
        pass

class DefaultJsonEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__

class ImageStreamingMessageContent(StreamingMessageContent):
    def __init__(self, image: np.ndarray) -> None:
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 75]
        _, encoded_img = cv2.imencode('.jpg', image, encode_params)
        self.image: str = base64.b64encode(encoded_img.tobytes()).decode('utf-8')

    def to_dict(self):
        return {"image": self.image}


@dataclass
class ValidationStreamingMessageContent(StreamingMessageContent):
    validation_result: ValidationResults

    def to_dict(self):
        """Convert to a format matching C# ValidationStreamingMessageContent"""
        return {"ValidationResult": self.validation_result.to_dict()}


class StreamingMessage:
    def __init__(self, type: StreamingMessageType, content: StreamingMessageContent) -> None:
        self.type = type
        self.content = json.dumps(content.to_dict(), cls=DefaultJsonEncoder)
