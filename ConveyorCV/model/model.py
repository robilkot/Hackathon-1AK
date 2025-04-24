from dataclasses import dataclass

from datetime import datetime
import numpy as np


# todo: информация о позиционировании наклейки
@dataclass
class ValidationParams:
    sticker_design: np.ndarray
    center: tuple
    sticker_size: tuple
    battery_size: tuple
    rotation: float



# todo: информация о позиционировании наклейки
@dataclass
class ValidationResults:
    sticker_present: bool
    sticker_matches_design: bool | None
    sticker_position: tuple | None  # todo документировать, доработать
    sticker_image: np.ndarray | None = None  # Captured sticker image
    sticker_position: tuple | None = None  # Center position
    sticker_size: tuple| None = None  # Width and height


@dataclass
class DetectionContext:
    image: np.ndarray
    detected_at: datetime = datetime.now
    seq_number: int = 0
    shape: np.ndarray | None = None  # BW mask
    processed_image: np.ndarray | None = None  # Aligned and cropped image
    validation_results: ValidationResults | None = None