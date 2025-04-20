from dataclasses import dataclass

from datetime import datetime
import numpy as np


# todo: информация о позиционировании наклейки
@dataclass
class ValidationParams:
    sticker_design: np.ndarray


# todo: информация о позиционировании наклейки
@dataclass
class ValidationResults:
    sticker_present: bool
    sticker_matches_design: bool | None
    sticker_position: tuple | None  # todo документировать, доработать


@dataclass
class DetectionContext:
    image: np.ndarray
    detected_at: datetime = datetime.now
    seq_number: int = 0
    shape: np.ndarray | None = None  # BW mask
    processed_image: np.ndarray | None = None  # Aligned and cropped image
    validation_results: ValidationResults | None = None