from pydantic import BaseModel, Field
from typing import Optional
import os
from utils.env import DOWNSCALE_WIDTH, DOWNSCALE_HEIGHT


class CameraSettings(BaseModel):
    phone_ip: str = Field(default="146.0.1")
    port: int = Field(default=8080)
    video_path: str = Field(default="data/cropped.mp4")


class ProcessingSettings(BaseModel):
    downscale_width: int = Field(default=DOWNSCALE_WIDTH)
    downscale_height: int = Field(default=DOWNSCALE_HEIGHT)
    threshold_value: int = Field(default=50)
    erosion_iterations: int = Field(default=7)
    dilation_iterations: int = Field(default=7)


class Settings(BaseModel):
    camera: CameraSettings = Field(default_factory=CameraSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    bg_photo_path: str = Field(default="data/frame_empty.png")
    sticker_design_path: str = Field(default="data/sticker_fixed.png")
    camera_type: str = Field(default="video")  # Options: "video", "ip"
    database_url: str = Field(default="sqlite:///../data/validation_logs.db")

    class Config:
        env_file = "../.env"


settings = Settings()


def update_settings(new_settings: Settings) -> Settings:
    global settings
    settings = new_settings
    os.environ["DOWNSCALE_WIDTH"] = str(settings.processing.downscale_width)
    os.environ["DOWNSCALE_HEIGHT"] = str(settings.processing.downscale_height)
    os.environ["PHONE_IP"] = settings.camera.phone_ip
    os.environ["VIDEO_PATH"] = settings.camera.video_path
    os.environ["BG_PHOTO_PATH"] = settings.bg_photo_path
    return settings


def get_settings() -> Settings:
    return settings