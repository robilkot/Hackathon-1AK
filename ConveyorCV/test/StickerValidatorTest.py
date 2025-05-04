import unittest
import cv2
import numpy as np

from algorithms.StickerValidator import StickerValidator
from utils.param_persistence import get_sticker_parameters
from model.model import DetectionContext, StickerValidationResult, StickerValidationParams
from utils.env import TEST_PRINT_EN

class StickerValidatorTest(unittest.TestCase):
    def __init__(self):
        super().__init__()
        self.sv = StickerValidator()

    @staticmethod
    def __compare_results(res1: StickerValidationResult, res2: StickerValidationResult):
        res = True
        if res1 is None and res2 is None:
            return True
        if res1 is None or res2 is None:
            if TEST_PRINT_EN:
                print("one of them is none")
            return False
        if res1.seq_number != res2.seq_number:
            if TEST_PRINT_EN:
                print("seq number diff", res1.seq_number, res2.seq_number)
            res = False
        if res1.sticker_size != res2.sticker_size:
            if TEST_PRINT_EN:
                print("sticker size diff", res1.sticker_size, res2.sticker_size)
            res = False
        if res1.detected_at != res2.detected_at:
            if TEST_PRINT_EN:
                print("detected at diff", res1.detected_at, res2.detected_at)
            res = False
        if res1.sticker_rotation != res2.sticker_rotation:
            if TEST_PRINT_EN:
                print("sticker rotation diff", res1.sticker_rotation, res2.sticker_rotation)
            res = False
        if res1.sticker_present != res2.sticker_present:
            if TEST_PRINT_EN:
                print("sticker present diff", res1.sticker_present, res2.sticker_present)
            res = False
        if res1.sticker_matches_design != res2.sticker_matches_design:
            if TEST_PRINT_EN:
                print("sticker matches design is diff", res1.sticker_matches_design, res2.sticker_matches_design)
            res = False
        if res1.sticker_position != res2.sticker_position:
            if TEST_PRINT_EN:
                print("sticker position diff", res1.sticker_position, res2.sticker_position)
            res = False
        if not np.array_equal(res1.sticker_image, res2.sticker_image):
            if TEST_PRINT_EN:
                print("image diff")
            res = False
        return res

    def __context_compare(self, cx1: DetectionContext, cx2: DetectionContext):
        if cx1 is None and cx2 is None:
            return True
        if cx1 is None or cx2 is None:
            if TEST_PRINT_EN:
                print("one of them is none")
            return False
        res = True
        if cx1.seq_number != cx2.seq_number:
            if TEST_PRINT_EN:
                print("seq number diff", cx1.seq_number, cx2.seq_number)
            res = False
        if not self.__compare_results(cx1.validation_results, cx2.validation_results):
            res = False
        if cx1.shape != cx2.shape:
            if TEST_PRINT_EN:
                print("shape diff", cx1.shape, cx2.shape)
            res = False
        if not np.array_equal(cx1.image, cx2.image):
            if TEST_PRINT_EN:
                print("image diff")
            res = False
        if not np.array_equal(cx1.processed_image, cx2.processed_image):
            if TEST_PRINT_EN:
                print("processed image diff")
            res = False
        if cx1.detected_at != cx2.detected_at:
            if TEST_PRINT_EN:
                print("detected at diff", cx1.detected_at, cx2.detected_at)
            res = False
        return res

    def __params_compare(self, p1: StickerValidationParams, p2: StickerValidationParams):
        if p1 is None and p2 is None:
            return True
        if p1 is None or p2 is None:
            if TEST_PRINT_EN:
                print("one of them is none")
            return False
        res = True
        if p1.sticker_size != p2.sticker_size:
            if TEST_PRINT_EN:
                print("size diff", p1.sticker_size, p2.sticker_size)
            res = False
        if p1.sticker_rotation != p2.sticker_rotation:
            if TEST_PRINT_EN:
                print("rotation diff", p1.sticker_rotation, p2.sticker_rotation)
            res = False
        if p1.sticker_center != p2.sticker_center:
            if TEST_PRINT_EN:
                print("center diff", p1.sticker_center, p2.sticker_center)
            res = False
        if not np.array_equal(p1.sticker_design, p2.sticker_design):
            if TEST_PRINT_EN:
                print("design diff")
            res = False
        return res

    def assert_params_valid(self, params: StickerValidationParams = None, expect_true: bool = True):
        p1 = get_sticker_parameters()

        if params is not None:
            p2 = params
        else:
            p2 = self.sv.get_parameters()

        res = self.__params_compare(p1, p2)

        if expect_true:
            self.assertTrue(res)
        else:
            self.assertFalse(res)

    def assert_object_valid(self, obj : str = None, image: str = None, expect_true : bool = True):

        if image is not None:
            bg = cv2.imread(image)
        else:
            bg = cv2.imread("data/frame_empty.png")

        if obj is not None:
            accum = cv2.imread(obj)
        else:
            accum = cv2.imread("test/test_data/object_valid.png")

        self.assertFalse(bg is None)
        self.assertFalse(accum is None)

        cx = DetectionContext(bg)
        cx.processed_image = accum
        cx = self.sv.validate(cx)

        res_empty = StickerValidationResult(False)
        res_empty.detected_at       = cx.detected_at
        res_empty.sticker_image     = cx.validation_results.sticker_image
        res_empty.sticker_matches_design   = False

        if expect_true:
            self.assertFalse(self.__compare_results(res_empty, cx.validation_results))
        else:
            self.assertTrue(self.__compare_results(res_empty, cx.validation_results))





