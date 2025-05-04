import math
import unittest
import cv2
import numpy as np
from scipy.stats.contingency import expected_freq

from algorithms.ShapeDetector import ShapeDetector
from algorithms.ShapeProcessor import ShapeProcessor
from model.model import DetectionContext
from utils.env import *

class ShapeProcessorTest(unittest.TestCase):
    sd: ShapeDetector = ShapeDetector()
    sp: ShapeProcessor = ShapeProcessor()

    def assert_accum_detected(self, obj : str = None, expected_true : bool = True):

        img = cv2.imread(obj)
        self.assertFalse(img is None)

        cx = DetectionContext(img)
        cx = self.sd.detect(cx)
        cx = self.sp.process(cx)

        if TEST_PRINT_EN:
            print(obj)
            print("")
            print(cx.processed_image)

        if expected_true:
            self.assertTrue(cx.processed_image is not None)
        else:
            self.assertTrue(cx.processed_image is None)

        return cx


    def __distance_between_points(self, p1, p2):
        return math.sqrt(math.fabs(p1[0] ^ 2 + p1[1] ^ 2 - p2[0] ^ 2 - p2[1] ^ 2))

    def __assert_contour_precise(self, koeff):
        cx1 = self.assert_accum_detected(obj='data/test_frame_with_accum_1280x720.png', expected_true=True)
        cx2 = self.assert_accum_detected(obj='data/test_frame_with_accum_contour_1280x720.png', expected_true=True)

        c1 = cx1.processed_image_corners
        c2 = cx2.processed_image_corners

        c1 = sorted(np.concatenate(c1).tolist())
        c2 = sorted(np.concatenate(c2).tolist())

        k = []
        k_i = 100
        diff = len(c1) - len(c2)
        diag = math.sqrt(DOWNSCALE_WIDTH*DOWNSCALE_WIDTH + DOWNSCALE_HEIGHT*DOWNSCALE_HEIGHT)

        self.assertTrue(diff >= 0)

        for i in range(0, len(c2)):
            for j in range(0, diff):
                k_i = min(k_i, self.__distance_between_points(c1[i], c2[i]) * 100 / diag)
            k.append(k_i)

        if TEST_PRINT_EN:
            print("distances:", k)
            print("max:", max(k))

        res = True
        for i in k:
            if i > koeff:
                res = False

        return res

    # def test_empty_frame(self):
    #     self.assert_accum_detected(obj="data/frame_empty_1280x720.png", expected_true=False)
    #
    # def test_valid_frame(self):
    #     self.assert_accum_detected(obj="data/frame_with_accum_1280x720.png", expected_true=True)

    def test_contour_precise_false(self):
        self.assertFalse(self.__assert_contour_precise(0.1))

    def test_contour_precise_true(self):
        self.assertTrue(self.__assert_contour_precise(1.0))


if __name__ == "__main__":
    unittest.main()
