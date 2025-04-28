from os import getenv
from dotenv import load_dotenv

load_dotenv()

PHONE_IP = getenv("PHONE_IP")
VIDEO_PATH = getenv("VIDEO_PATH")
BG_PHOTO_PATH = getenv("BG_PHOTO_PATH")
DOWNSCALE_WIDTH = int(getenv("DOWNSCALE_WIDTH"))
DOWNSCALE_HEIGHT = int(getenv("DOWNSCALE_HEIGHT"))
API_PORT = int(getenv("API_PORT"))
