import abc
import base64
import json
from dataclasses import dataclass
from typing import Optional, Tuple, Union
from dataclasses import dataclass, field

from datetime import datetime
from json import JSONEncoder
from sqlalchemy import create_engine, Column, Integer, Float, Boolean, DateTime, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from enum import IntEnum

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
            "StickerDesign": image_bytes,
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
class StickerValidationResult:
    sticker_present: bool
    sticker_matches_design: Optional[bool] = None
    sticker_image: np.ndarray | None = None
    sticker_position: Optional[Tuple[float, float]] = None
    sticker_size: Optional[Tuple[float, float]] = None
    sticker_rotation: Optional[float] = None
    seq_number: int = 0
    detected_at: datetime = field(default_factory=datetime.now)

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
    detected_at: datetime = field(default_factory=datetime.now)
    seq_number: int = 0
    shape: np.ndarray | None = None  # BW mask
    processed_image: np.ndarray | None = None  # Aligned and cropped image
    validation_results: StickerValidationResult | None = None

    def to_dict(self) -> dict:
        """Serialize DetectionContext to dictionary"""
        result = {
            "seq_number": self.seq_number,
            "detected_at": self.detected_at.isoformat()
        }

        if self.image is not None:
            _, buffer = cv2.imencode('.jpg', self.image)
            result["image"] = base64.b64encode(buffer).decode('utf-8')

        if self.shape is not None:
            _, buffer = cv2.imencode('.jpg', self.shape)
            result["shape"] = base64.b64encode(buffer).decode('utf-8')

        if self.processed_image is not None:
            _, buffer = cv2.imencode('.jpg', self.processed_image)
            result["processed_image"] = base64.b64encode(buffer).decode('utf-8')

        # Include validation results
        if self.validation_results:
            result["validation_results"] = self.validation_results.to_dict()

        return result

    @classmethod
    def from_dict(cls, data: dict) -> "DetectionContext":
        """Create DetectionContext from dictionary data"""
        ctx = cls(np.array([]))

        # Set basic properties
        ctx.seq_number = data.get("seq_number", 0)
        if "detected_at" in data:
            ctx.detected_at = datetime.fromisoformat(data["detected_at"])

        # Decode images
        if "image" in data:
            img_data = base64.b64decode(data["image"])
            ctx.image = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)

        if "shape" in data:
            shape_data = base64.b64decode(data["shape"])
            ctx.shape = cv2.imdecode(np.frombuffer(shape_data, np.uint8), cv2.IMREAD_GRAYSCALE)

        if "processed_image" in data:
            img_data = base64.b64decode(data["processed_image"])
            ctx.processed_image = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)

        # Reconstruct validation results if present
        if "validation_results" in data:
            from model.model import StickerValidationResult
            ctx.validation_results = StickerValidationResult.from_dict(data["validation_results"])

        return ctx


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
    validation_result: StickerValidationResult

    def to_dict(self):
        """Convert to a format matching C# ValidationStreamingMessageContent"""
        return {"ValidationResult": self.validation_result.to_dict()}


class StreamingMessage:
    def __init__(self, type: StreamingMessageType, content: StreamingMessageContent) -> None:
        self.type = type
        self.content = json.dumps(content.to_dict(), cls=DefaultJsonEncoder)

Base = declarative_base()

class ValidationLog(Base):
    __tablename__ = "validation_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True)
    seq_number = Column(Integer)
    sticker_present = Column(Boolean)
    sticker_matches_design = Column(Boolean, nullable=True)
    sticker_position_x = Column(Float, nullable=True)
    sticker_position_y = Column(Float, nullable=True)
    sticker_size_width = Column(Float, nullable=True)
    sticker_size_height = Column(Float, nullable=True)
    sticker_rotation = Column(Float, nullable=True)

    def to_dict(self):
        """Convert ValidationLog to a format suitable for API response"""
        return {
            "Id": self.id,
            "Timestamp": self.timestamp,
            "SeqNumber": self.seq_number,
            "StickerPresent": self.sticker_present,
            "StickerMatchesDesign": self.sticker_matches_design,
            "StickerPosition": {
                "x": self.sticker_position_x,
                "y": self.sticker_position_y
            } if self.sticker_position_x is not None and self.sticker_position_y is not None else None,
            "StickerSize": {
                "width": self.sticker_size_width,
                "height": self.sticker_size_height
            } if self.sticker_size_width is not None and self.sticker_size_height is not None else None,
            "StickerRotation": self.sticker_rotation
        }

    @classmethod
    def paginate(cls, db, start_date=None, end_date=None, page=1, page_size=100):
        """Class method to paginate validation logs with filtering"""
        query = db.query(cls)

        if start_date:
            query = query.filter(cls.timestamp >= start_date)

        if end_date:
            query = query.filter(cls.timestamp <= end_date)

        total_count = query.count()
        query = query.order_by(cls.timestamp.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        results = query.all()
        logs = [log.to_dict() for log in results]

        return {
            "Total": total_count,
            "Page": page,
            "PageSize": page_size,
            "Pages": (total_count + page_size - 1) // page_size,
            "Logs": logs
        }