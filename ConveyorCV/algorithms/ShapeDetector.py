import cv2
import numpy as np

from backend.settings import get_settings
from model.model import DetectionContext
from utils.downscale import downscale


class ShapeDetector:
    def __init__(self, settings=None):
        # todo: четко определить размер ядра
        self.kernel = np.ones((12, 12), np.uint8)
        self.settings = settings or get_settings()
        self.image_conveyor_empty = cv2.imread(self.settings.bg_photo_path)
        self.image_conveyor_empty = downscale(self.image_conveyor_empty, self.settings.processing.downscale_width, self.settings.processing.downscale_height)
        self.image_conveyor_empty = cv2.morphologyEx(self.image_conveyor_empty, cv2.MORPH_CLOSE, self.kernel, iterations=3)

    def detect(self, context: DetectionContext) -> DetectionContext:
        image = context.image
        image = cv2.morphologyEx(image, cv2.MORPH_CLOSE, self.kernel, iterations=3)

        image_diff = cv2.absdiff(image, self.image_conveyor_empty)
        image_gray = cv2.cvtColor(image_diff, cv2.COLOR_BGR2GRAY)
        image_blurred = cv2.GaussianBlur(image_gray, (11, 11), 0)

        # todo: четко определить порог
        _, image_thresh = cv2.threshold(image_blurred, 50, 255, cv2.THRESH_BINARY)
        image_eroded = cv2.erode(image_thresh, None, iterations=7)
        canny = cv2.Canny(image_eroded, 0, 200)
        image_dilated = cv2.dilate(canny, None, iterations=7)

        # todo: четко определить размер ядра
        image_dilated_kernel = np.ones((15, 15), np.uint8)
        image_dilated = cv2.morphologyEx(image_dilated, cv2.MORPH_CLOSE, image_dilated_kernel, iterations=7)

        context.shape = image_dilated
        return context