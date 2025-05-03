import json
import os
from functools import lru_cache
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class CameraSettings(BaseModel):
    phone_ip: str = "192.168.1.46"
    port: int = 8080
    video_path: str = "data/cropped.mp4"


class ProcessingSettings(BaseModel):
    downscale_width: int = 1280
    downscale_height: int = 720


class ValidationSettings(BaseModel):
    position_tolerance_percent: float = 10.0
    rotation_tolerance_degrees: float = 15.0
    size_ratio_tolerance: float = 0.15


class DetectionSettings(BaseModel):
    detection_border_left: float = 0.32
    detection_border_right: float = 0.68
    detection_line_height: float = 0.5


class Settings(BaseModel):
    camera_type: str = "video"  # "video" or "ip"
    bg_photo_path: str = "data/frame_empty.png"
    database_url: str = "sqlite:///./data/validation_logs.db"
    sticker_params_file: str = "data/sticker_params.json"
    sticker_design_path: str = "data/sticker_fixed.png"
    sticker_output_path: str = "data/sticker_design.png"
    settings_file_path: str = "data/settings.json"
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    camera: CameraSettings = Field(default_factory=CameraSettings)
    validation: ValidationSettings = Field(default_factory=ValidationSettings)
    detection: DetectionSettings = Field(default_factory=DetectionSettings)

    def save_to_file(self, file_path: str = "data/settings/app_settings.json"):
        """Save settings to JSON file"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(self.model_dump(), f, indent=2)

    def to_dict(self) -> dict:
        """Convert settings to dictionary format"""
        return {
            "database_url": self.database_url,
            "sticker_params_file": self.sticker_params_file,
            "sticker_design_path": self.sticker_design_path,
            "sticker_output_path": self.sticker_output_path,
            "validation": {
                "position_tolerance_percent": self.validation.position_tolerance_percent,
                "rotation_tolerance_degrees": self.validation.rotation_tolerance_degrees,
                "size_ratio_tolerance": self.validation.size_ratio_tolerance
            },
            "detection": {
                "detection_border_left": self.detection.detection_border_left,
                "detection_border_right": self.detection.detection_border_right,
                "detection_line_height": self.detection.detection_line_height
            },
            "processing": {
                "downscale_width": self.processing.downscale_width,
                "downscale_height": self.processing.downscale_height
            },
            "camera": {
                "phone_ip": self.camera.phone_ip,
                "port": self.camera.port,
                "video_path": self.camera.video_path
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """Create Settings object from dictionary data"""
        validation_data = data.pop("validation", {})
        detection_data = data.pop("detection", {})
        processing_data = data.pop("processing", {})
        camera_data = data.pop("camera", {})

        instance = cls(**data)

        if validation_data:
            instance.validation.position_tolerance_percent = validation_data.get(
                "position_tolerance_percent", instance.validation.position_tolerance_percent
            )
            instance.validation.rotation_tolerance_degrees = validation_data.get(
                "rotation_tolerance_degrees", instance.validation.rotation_tolerance_degrees
            )
            instance.validation.size_ratio_tolerance = validation_data.get(
                "size_ratio_tolerance", instance.validation.size_ratio_tolerance
            )

        if detection_data:
            instance.detection.detection_border_left = detection_data.get(
                "detection_border_left", instance.detection.detection_border_left
            )
            instance.detection.detection_border_right = detection_data.get(
                "detection_border_right", instance.detection.detection_border_right
            )
            instance.detection.detection_line_height = detection_data.get(
                "detection_line_height", instance.detection.detection_line_height
            )

        if processing_data:
            instance.processing.downscale_width = processing_data.get(
                "downscale_width", instance.processing.downscale_width
            )
            instance.processing.downscale_height = processing_data.get(
                "downscale_height", instance.processing.downscale_height
            )

        if camera_data:
            instance.camera.phone_ip = camera_data.get(
                "phone_ip", instance.camera.phone_ip
            )
            instance.camera.port = camera_data.get(
                "port", instance.camera.port
            )
            instance.camera.video_path = camera_data.get(
                "video_path", instance.camera.video_path
            )

        return instance

_settings: Optional[Settings] = None
_settings_file = os.environ.get("SETTINGS_FILE", "../data/settings/app_settings.json")


@lru_cache
def get_settings() -> Settings:
    """Get application settings, loading from file if available"""
    global _settings

    if _settings is None:
        _settings = load_settings(_settings_file)

    return _settings


def load_settings(file_path: str = _settings_file) -> Settings:
    """Load settings from JSON file if it exists"""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                return Settings.from_dict(data)
        except Exception as e:
            print(f"Error loading settings: {e}")

    return Settings()


def reset_settings() -> Settings:
    """Reset settings to default values"""
    global _settings
    _settings = Settings()
    get_settings.cache_clear()
    return _settings


def save_settings(settings: Settings) -> None:
    """Save settings and update global instance"""
    global _settings
    _settings = settings

    os.makedirs(os.path.dirname(_settings_file), exist_ok=True)

    with open(_settings_file, 'w') as f:
        json.dump(settings.to_dict(), f, indent=2)

    get_settings.cache_clear()