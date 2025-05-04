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
    rotation_tolerance_degrees: float = 5.0
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
            "DatabaseUrl": self.database_url,
            "StickerParamsFile": self.sticker_params_file,
            "StickerDesignPath": self.sticker_design_path,
            "StickerOutputPath": self.sticker_output_path,
            "CameraType": self.camera_type,
            "BgPhotoPath": self.bg_photo_path,
            "SettingsFilePath": self.settings_file_path,
            "Validation": {
                "PositionTolerancePercent": self.validation.position_tolerance_percent,
                "RotationToleranceDegrees": self.validation.rotation_tolerance_degrees,
                "SizeRatioTolerance": self.validation.size_ratio_tolerance
            },
            "Detection": {
                "DetectionBorderLeft": self.detection.detection_border_left,
                "DetectionBorderRight": self.detection.detection_border_right,
                "DetectionLineHeight": self.detection.detection_line_height
            },
            "Processing": {
                "DownscaleWidth": self.processing.downscale_width,
                "DownscaleHeight": self.processing.downscale_height
            },
            "Camera": {
                "PhoneIp": self.camera.phone_ip,
                "Port": self.camera.port,
                "VideoPath": self.camera.video_path
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """Create Settings object from dictionary data"""
        settings_data = {
            "database_url": data.get("DatabaseUrl", "sqlite:///./data/validation_logs.db"),
            "sticker_params_file": data.get("StickerParamsFile", "data/sticker_params.json"),
            "sticker_design_path": data.get("StickerDesignPath", "data/sticker_fixed.png"),
            "sticker_output_path": data.get("StickerOutputPath", "data/sticker_design.png"),
            "camera_type": data.get("CameraType", "video"),
            "bg_photo_path": data.get("BgPhotoPath", "data/frame_empty.png"),
            "settings_file_path": data.get("SettingsFilePath", "data/settings.json")
        }

        instance = cls(**settings_data)

        validation_data = data.get("Validation", {})
        if validation_data:
            instance.validation.position_tolerance_percent = validation_data.get(
                "PositionTolerancePercent", instance.validation.position_tolerance_percent
            )
            instance.validation.rotation_tolerance_degrees = validation_data.get(
                "RotationToleranceDegrees", instance.validation.rotation_tolerance_degrees
            )
            instance.validation.size_ratio_tolerance = validation_data.get(
                "SizeRatioTolerance", instance.validation.size_ratio_tolerance
            )

        detection_data = data.get("Detection", {})
        if detection_data:
            instance.detection.detection_border_left = detection_data.get(
                "DetectionBorderLeft", instance.detection.detection_border_left
            )
            instance.detection.detection_border_right = detection_data.get(
                "DetectionBorderRight", instance.detection.detection_border_right
            )
            instance.detection.detection_line_height = detection_data.get(
                "DetectionLineHeight", instance.detection.detection_line_height
            )

        processing_data = data.get("Processing", {})
        if processing_data:
            instance.processing.downscale_width = processing_data.get(
                "DownscaleWidth", instance.processing.downscale_width
            )
            instance.processing.downscale_height = processing_data.get(
                "DownscaleHeight", instance.processing.downscale_height
            )

        camera_data = data.get("Camera", {})
        if camera_data:
            instance.camera.phone_ip = camera_data.get(
                "PhoneIp", instance.camera.phone_ip
            )
            instance.camera.port = camera_data.get(
                "Port", instance.camera.port
            )
            instance.camera.video_path = camera_data.get(
                "VideoPath", instance.camera.video_path
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