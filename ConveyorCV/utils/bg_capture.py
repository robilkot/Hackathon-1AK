
import base64
import logging
import os
from datetime import datetime

import cv2
import numpy as np

from backend.settings import get_settings, save_settings


logger = logging.getLogger(__name__)

def save_and_set_empty_conveyor_background(image_data_base64):
    """
    Save uploaded image as empty conveyor background and apply it to settings

    Args:
        image_data_base64: Base64 encoded string of image data

    Returns:
        dict: Result with success status, message and path
    """
    try:
        os.makedirs("data", exist_ok=True)

        # Decode base64 string to image
        image_data = base64.b64decode(image_data_base64)
        image_array = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if frame is None:
            return {"success": False, "message": "Invalid image data"}

        # Save image with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/frame_empty_{timestamp}.png"
        cv2.imwrite(filename, frame)

        # Update settings
        settings = get_settings()
        settings.bg_photo_path = filename
        save_settings(settings)

        return {
            "success": True,
            "message": "Empty conveyor background set from uploaded image",
            "path": filename
        }
    except Exception as e:
        logger.error(f"Failed to set empty conveyor background: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}