# utils/bg_capture.py
import os
import cv2
import logging
from datetime import datetime

from backend.settings import get_settings, save_settings

logger = logging.getLogger(__name__)


def capture_empty_conveyor_background(camera):
    """
    Capture current frame from camera and save it as empty conveyor background

    Args:
        camera: Camera interface to capture frame from

    Returns:
        dict: Result with success status, message and path
    """
    try:
        os.makedirs("data", exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/frame_empty_{timestamp}.png"

        camera.connect()
        frame = camera.get_frame()

        if frame is None:
            return {"success": False, "message": "Failed to capture frame from camera"}

        cv2.imwrite(filename, frame)

        settings = get_settings()
        settings.bg_photo_path = filename
        save_settings(settings)

        return {
            "success": True,
            "message": "Empty conveyor background captured",
            "path": filename
        }

    except Exception as e:
        logger.error(f"Failed to capture empty conveyor background: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}