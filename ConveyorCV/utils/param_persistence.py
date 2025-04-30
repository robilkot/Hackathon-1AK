import json
import os
import cv2
from model.model import StickerValidationParams

PARAMS_FILE = "../data/sticker_params.json"
DEFAULT_STICKER_DESIGN_PATH = "../data/sticker_fixed.png"


def get_default_sticker_parameters():
    """Return default sticker validation parameters"""
    sticker_design = cv2.imread(DEFAULT_STICKER_DESIGN_PATH)

    if sticker_design is None:
        raise Exception(f"Default sticker design not found at {DEFAULT_STICKER_DESIGN_PATH}")

    return StickerValidationParams(
        sticker_design=sticker_design,
        sticker_center=(50.0, 50.0),  # Default center point
        acc_size=(200.0, 200.0),  # Default acceptable size
        sticker_size=(100.0, 100.0),  # Default sticker size
        sticker_rotation=0.0  # Default rotation angle
    )


def save_sticker_parameters(params: StickerValidationParams):
    """Save sticker parameters to a JSON file with the sticker design as a separate image file"""
    os.makedirs(os.path.dirname(PARAMS_FILE), exist_ok=True)

    image_path = "../data/sticker_design.png"
    cv2.imwrite(image_path, params.sticker_design)

    params_dict = params.to_dict()

    if "StickerDesign" in params_dict:
        del params_dict["StickerDesign"]

    params_dict["sticker_design_path"] = image_path

    with open(PARAMS_FILE, 'w') as f:
        json.dump(params_dict, f)


def load_sticker_parameters():
    """Load sticker parameters from a JSON file"""
    if not os.path.exists(PARAMS_FILE):
        return None

    try:
        with open(PARAMS_FILE, 'r') as f:
            params_dict = json.load(f)

        image_path = params_dict.pop("sticker_design_path")
        if os.path.exists(image_path):
            params_dict["sticker_design"] = cv2.imread(image_path)
            return StickerValidationParams.from_dict(params_dict)
    except Exception as e:
        print(f"Error loading sticker parameters: {e}")

    return None


def get_sticker_parameters():
    """Get sticker parameters from persistence if available, otherwise use defaults"""
    params = load_sticker_parameters()
    if params is not None:
        return params

    return get_default_sticker_parameters()