import logging
from queue import Queue

import cv2
from numpy import median

from algorithms.InvariantTM import invariant_match_template
from model.model import StickerValidationParams, DetectionContext, StickerValidationResult

logger = logging.getLogger(__name__)
combined_validation_results = Queue()


class StickerValidator:
    def __init__(self, params: StickerValidationParams = None):
        if params is None:
            from utils.param_persistence import get_sticker_parameters
            self.__params = get_sticker_parameters()
        else:
            self.__params = params

        self.__last_processed_acc_number: int = 1
        self.__last_processed_acc_detections: list[DetectionContext] = []

    def set_parameters(self, sticker_params: StickerValidationParams):
        self.__params = sticker_params

    def get_parameters(self) -> StickerValidationParams:
        return self.__params

    def validate(self, context: DetectionContext) -> DetectionContext:
        if self.__last_processed_acc_number != context.seq_number:
            self.process_combined_validation()
            self.__last_processed_acc_number = context.seq_number

        img_bgr = context.processed_image
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_height, img_width = img_rgb.shape[:2]

        template_bgr = self.__params.sticker_design
        template_rgb = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2RGB)

        points_list = invariant_match_template(rgbimage=img_rgb, rgbtemplate=template_rgb, method="TM_CCOEFF_NORMED",
                                               matched_thresh=0.5, rot_range=[-15, 15], rot_interval=2,
                                               scale_range=[15, 50], scale_interval=5, rm_redundant=True, minmax=True)

        if len(points_list) > 1:
            raise Exception("more than 2 stickers?")

        # todo различать случай когда наклейка есть, но неверный дизайн
        sticker_present = len(points_list) > 0
        sticker_matches_design = sticker_present

        context.validation_results = StickerValidationResult(
            sticker_present=sticker_present,
            sticker_matches_design=sticker_matches_design,
            sticker_image=context.processed_image,
            seq_number=context.seq_number,
            detected_at=context.detected_at
        )

        if sticker_present and points_list[0]:
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

            #todo add it to settings
            POSITION_TOLERANCE_PERCENT = 10.0  # % of accumulator size
            ROTATION_TOLERANCE_DEGREES = 5.0  # degrees
            SIZE_RATIO_TOLERANCE = 0.15  # % difference in expected ratio

            expected_center_x = self.__params.sticker_center[0] / self.__params.acc_size[0] * img_width
            expected_center_y = self.__params.sticker_center[1] / self.__params.acc_size[1] * img_height

            position_tolerance_x = img_width * POSITION_TOLERANCE_PERCENT / 100
            position_tolerance_y = img_height * POSITION_TOLERANCE_PERCENT / 100

            logger.info(f"pos "
                        f"exp_center: ({expected_center_x:.1f}, {expected_center_y:.1f}) "
                        f"act_center: ({x:.1f}, {y:.1f}) "
                        f"tolerance: ({position_tolerance_x:.1f}, {position_tolerance_y:.1f}) "
                        f"rotation: {rotation:.1f} ")

            position_valid = (
                    abs(x - expected_center_x) <= position_tolerance_x and
                    abs(y - expected_center_y) <= position_tolerance_y
            )

            rotation_valid = abs(rotation - self.__params.sticker_rotation) <= ROTATION_TOLERANCE_DEGREES

            #todo calculate one time
            expected_width_ratio = self.__params.sticker_size[0] / self.__params.acc_size[0]
            expected_height_ratio = self.__params.sticker_size[1] / self.__params.acc_size[1]

            actual_width_ratio = sticker_size[0] / img_width
            actual_height_ratio = sticker_size[1] / img_height

            logger.info(f"size "
                        f"exp_ratio: ({expected_width_ratio:.4f} ({self.__params.sticker_size[0]:.1f}/{self.__params.acc_size[0]:.1f}), {expected_height_ratio:.4f} ({self.__params.sticker_size[1]:.1f}/{self.__params.acc_size[1]:.1f})) "
                        f"act_ratio: ({actual_width_ratio:.4f} ({sticker_size[0]:.1f}/{img_width:.1f}) ,{actual_height_ratio:.4f} ({sticker_size[1]:.1f}/{img_height:.1f})) ")

            size_valid = (
                    abs(actual_width_ratio - expected_width_ratio) <= SIZE_RATIO_TOLERANCE and
                    abs(actual_height_ratio - expected_height_ratio) <= SIZE_RATIO_TOLERANCE
            )

            sticker_matches_design = position_valid and rotation_valid and size_valid
            context.validation_results.sticker_matches_design = sticker_matches_design

            logger.info(f"SEQ #{context.seq_number} "
                        f"total: {sticker_matches_design} "
                        f"position: {position_valid} "
                        f"rotation: {rotation_valid} "
                        f"size: {size_valid} ")

        self.__last_processed_acc_detections.append(context)
        return context

    def process_combined_validation(self):
        results = list([ctx.validation_results for ctx in self.__last_processed_acc_detections
                        if ctx.seq_number == self.__last_processed_acc_number])
        if len(results) == 0:
            return

        for i, test in enumerate(results):
            assert test.seq_number == self.__last_processed_acc_number, 'Wrong seq_number in combined validation!'
            # logger.info(f'{test.seq_number}')
            cv2.imwrite(f'data/{test.seq_number}_{i}.jpg', test.sticker_image)

        # Get most common value for sticker_present
        sticker_present = max(set(r.sticker_present for r in results), key=list(results).count)

        # Get median values for optional numeric fields
        positions = list([r.sticker_position for r in results if r.sticker_position is not None])
        sizes = list([r.sticker_size for r in results if r.sticker_size is not None])
        rotations = list([r.sticker_rotation for r in results if r.sticker_rotation is not None])

        if sticker_present:
            median_position = tuple(median(x) for x in zip(*positions)) if positions else None
            median_size = tuple(median(x) for x in zip(*sizes)) if sizes else None
            median_rotation = median(rotations) if rotations else None
        else:
            median_position = None
            median_size = None
            median_rotation = None

        # Get most common value for sticker_matches_design
        matches = [r.sticker_matches_design for r in results if r.sticker_matches_design is not None]
        sticker_matches_design = max(set(matches), key=matches.count) if matches else None

        result = StickerValidationResult(
            sticker_present=sticker_present,
            sticker_matches_design=sticker_matches_design,
            sticker_image=results[0].sticker_image,  # todo take nearest to median values by rotation and location
            sticker_position=median_position,
            sticker_size=median_size,
            sticker_rotation=median_rotation,
            seq_number=results[0].seq_number,
            detected_at=results[0].detected_at
        )

        combined_validation_results.put(result)
        self.__last_processed_acc_detections = []
