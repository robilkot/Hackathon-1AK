import logging
import time
from queue import Queue
from collections import Counter
import cv2
import numpy as np
from numpy import median
from sqlalchemy.dialects.mssql.information_schema import sequences

from algorithms.InvariantTM import invariant_match_template
from backend.settings import get_settings
from model.model import StickerValidationParams, DetectionContext, StickerValidationResult

logger = logging.getLogger(__name__)
combined_validation_results = Queue()


def vignette(img, level=4):
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    height, width = img.shape[:2]

    # Generate vignette mask using Gaussian kernels.
    X_resultant_kernel = cv2.getGaussianKernel(width, width / level)
    Y_resultant_kernel = cv2.getGaussianKernel(height, height / level)

    # Generating resultant_kernel matrix.
    kernel = Y_resultant_kernel * X_resultant_kernel.T
    mask = kernel / kernel.max()

    img_vignette = np.copy(img)

    for i in range(3):
        img_vignette[:, :, i] = img_vignette[:, :, i] * mask

    img_vignette = cv2.cvtColor(img_vignette, cv2.COLOR_RGB2GRAY)
    return img_vignette


def is_sticker_present(img: np.ndarray, threshold) -> bool:
    image = cv2.medianBlur(img, 21)
    image = cv2.Canny(image, 100, 200)

    image_dilated_kernel = np.ones((6, 6), np.uint8)
    image = cv2.morphologyEx(image, cv2.MORPH_CLOSE, image_dilated_kernel, iterations=1)
    image = cv2.morphologyEx(image, cv2.MORPH_DILATE, image_dilated_kernel, iterations=10)
    image = vignette(image)

    med = np.mean(image)
    return bool(med > threshold)


class StickerValidator:
    def __init__(self, params: StickerValidationParams = None):
        self.__last_processed_acc_number: int = 1
        self.__last_processed_acc_detections: list[DetectionContext] = []
        self.__expected_ratio_w: float = 0
        self.__expected_ratio_h: float = 0
        self.__params: StickerValidationParams | None = None

        if params is None:
            from utils.param_persistence import get_sticker_parameters
            params = get_sticker_parameters()

        self.set_parameters(params)

    def set_parameters(self, sticker_params: StickerValidationParams):
        self.__params = sticker_params
        self.__expected_ratio_w = self.__params.sticker_size[0] / self.__params.acc_size[0]
        self.__expected_ratio_h = self.__params.sticker_size[1] / self.__params.acc_size[1]

    def get_parameters(self) -> StickerValidationParams:
        return self.__params

    def validate(self, context: DetectionContext) -> DetectionContext:
        if self.__last_processed_acc_number != context.seq_number:
            self.process_combined_validation()
            self.__last_processed_acc_number = context.seq_number

        img_bgr = context.processed_image
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_height, img_width = img_rgb.shape[:2]

        # todo make parameter for threshold
        sticker_present = is_sticker_present(img_rgb, 30)

        context.validation_results = StickerValidationResult(
            sticker_image=context.processed_image,
            sticker_present=sticker_present,
            seq_number=context.seq_number,
            detected_at=context.detected_at
        )

        if sticker_present:
            template_bgr = self.__params.sticker_design
            template_rgb = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2RGB)

            # "TM_CCOEFF":
            # "TM_CCOEFF_NORMED":
            # "TM_CCORR":
            # "TM_CCORR_NORMED":
            # "TM_SQDIFF":
            # "TM_SQDIFF_NORMED":
            # todo parametric scale_range!!!
            points_list = invariant_match_template(rgbimage=img_rgb, rgbtemplate=template_rgb, method="TM_CCORR_NORMED",
                                                   matched_thresh=0.5, rot_range=[-10, 10], rot_interval=1,
                                                   scale_range=[10, 25], scale_interval=4, rm_redundant=True, minmax=True)

            if len(points_list) > 1:
                logger.error(f"more than 2 stickers? len(points_list) == {len(points_list)}")

            if len(points_list) == 0:
                logger.info(f"SEQ {context.seq_number} wrong design")
                context.validation_results.sticker_matches_design = False
            else:
                rotation = points_list[0][1]
                scale = points_list[0][2]
                confidence = points_list[0][3]

                sticker_size = (template_rgb.shape[1] * scale / 100, template_rgb.shape[0] * scale / 100)
                x, y = points_list[0][0]
                x, y = x + sticker_size[0] / 2, y + sticker_size[1] / 2
                position_tuple = (x, y)
                size_tuple = (float(sticker_size[0]), float(sticker_size[1]))

                context.validation_results.sticker_position = position_tuple
                context.validation_results.sticker_rotation = float(rotation)
                context.validation_results.sticker_size = size_tuple

                settings = get_settings()
                position_tolerance_percent = settings.validation.position_tolerance_percent
                rotation_tolerance_degrees = settings.validation.rotation_tolerance_degrees
                size_ratio_tolerance = settings.validation.size_ratio_tolerance

                expected_center_x = self.__params.sticker_center[0] / self.__params.acc_size[0] * img_width
                expected_center_y = self.__params.sticker_center[1] / self.__params.acc_size[1] * img_height

                position_tolerance_x = img_width * position_tolerance_percent / 100
                position_tolerance_y = img_height * position_tolerance_percent / 100

                position_valid = (
                        abs(x - expected_center_x) <= position_tolerance_x and
                        abs(y - expected_center_y) <= position_tolerance_y
                )

                rotation_valid = abs(rotation - self.__params.sticker_rotation) <= rotation_tolerance_degrees

                actual_ratio_w = sticker_size[0] / img_width
                actual_ratio_h = sticker_size[1] / img_height

                size_valid = (
                        abs(actual_ratio_w - self.__expected_ratio_w) <= size_ratio_tolerance and
                        abs(actual_ratio_h - self.__expected_ratio_h) <= size_ratio_tolerance
                )

                sticker_matches_design = position_valid and rotation_valid and size_valid
                context.validation_results.sticker_matches_design = sticker_matches_design

                # if rotation > 1 or rotation < -1:
                    # cv2.imwrite(f'data/{context.seq_number}_{time.thread_time()}.png', img_bgr)

                logger.info(f"#{context.seq_number} "
                            f"scale {scale} "
                            f"total: {'OK' if sticker_matches_design else 'ERROR'} "
                            f"pos: {'OK' if position_valid else 'ERROR'} "
                            f"rot: {'OK' if rotation_valid else 'ERROR'} "
                            f"siz: {'OK' if size_valid else 'ERROR'} "
                            f"center: {x:.1f}/{expected_center_x:.1f}, {y:.1f}/{expected_center_y:.1f} "
                            f"(tolerance: {position_tolerance_x:.1f}, {position_tolerance_y:.1f}) "
                            f"rot: {rotation:.1f} "
                            f"asp: {actual_ratio_w:.2f}/{self.__expected_ratio_w:.2f}, {actual_ratio_h:.2f}/{self.__expected_ratio_h:.2f} ")
        else:
            logger.info(f"SEQ {context.seq_number} sticker NOT present")

        self.__last_processed_acc_detections.append(context)
        return context

    def process_combined_validation(self):
        if not self.__last_processed_acc_detections:
            return

        current_results = [ctx.validation_results for ctx in self.__last_processed_acc_detections
                           if ctx and ctx.validation_results and ctx.seq_number == self.__last_processed_acc_number]

        if not current_results:
            return

        present_values = [r.sticker_present for r in current_results]
        sticker_present = Counter(present_values).most_common(1)[0][0] if present_values else False

        for i, test in enumerate(current_results):
            assert test.seq_number == self.__last_processed_acc_number, 'Wrong seq_number in combined validation!'
            # logger.info(f'{test.seq_number}')
            # cv2.imwrite(f'data/{test.seq_number}_{i}.jpg', test.sticker_image)

        sticker_matches_design = None
        median_position = None
        median_size = None
        median_rotation = None
        best_image = None

        if sticker_present:
            positions = [r.sticker_position for r in current_results if r.sticker_position is not None]
            sizes = [r.sticker_size for r in current_results if r.sticker_size is not None]
            rotations = [r.sticker_rotation for r in current_results if r.sticker_rotation is not None]

            if positions:
                median_position = tuple(median([pos[i] for pos in positions]) for i in range(2))

            if sizes:
                median_size = tuple(median([size[i] for size in sizes]) for i in range(2))

            if rotations:
                median_rotation = median(rotations)

            matches = [r.sticker_matches_design for r in current_results if r.sticker_matches_design is not None]
            if matches:
                sticker_matches_design = Counter(matches).most_common(1)[0][0]

            if median_position and median_rotation:
                def distance_to_median(result):
                    if not result.sticker_position or result.sticker_rotation is None:
                        return float('inf')

                    pos_distance = sum((result.sticker_position[i] - median_position[i]) ** 2 for i in range(2)) ** 0.5
                    rot_distance = abs(result.sticker_rotation - median_rotation)
                    return pos_distance + rot_distance * 5  # Weight rotation differences

                best_result = min(current_results, key=distance_to_median)
                best_image = best_result.sticker_image
            else:
                best_image = current_results[0].sticker_image
        else:
            best_image = current_results[0].sticker_image

        result = StickerValidationResult(
            sticker_present=sticker_present,
            sticker_matches_design=sticker_matches_design,
            sticker_image=best_image,
            sticker_position=median_position,
            sticker_size=median_size,
            sticker_rotation=median_rotation,
            seq_number=self.__last_processed_acc_number,
            detected_at=current_results[0].detected_at
        )

        combined_validation_results.put(result)
        self.__last_processed_acc_detections = []