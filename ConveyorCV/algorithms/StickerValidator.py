import datetime
from threading import Timer

import cv2
from numpy import median

from algorithms.InvariantTM import invariant_match_template
from model.model import StickerValidationParams, DetectionContext, StickerValidationResult

class StickerValidator:
    def __init__(self, params: StickerValidationParams):
        self.__params = params
        self.__combined_validation_result: StickerValidationResult | None = None
        self.__last_processed_acc_number: int = 1
        self.__last_processed_acc_detections: list[DetectionContext] = []
        self.__validation_timer: Timer | None = None
        self.__validation_max_interval: float = 1.5  # Maximum interval in seconds before performing combined validation

    def set_parameters(self, sticker_params: StickerValidationParams):
        self.__params = sticker_params

    def get_parameters(self) -> StickerValidationParams:
        return self.__params

    def validate(self, context: DetectionContext) -> DetectionContext:
        if self.__validation_timer is not None:
            self.__validation_timer.cancel()
        self.__validation_timer = Timer(self.__validation_max_interval, self.__process_combined_validation)
        self.__validation_timer.start()

        if self.__last_processed_acc_number != context.seq_number:
            self.__process_combined_validation()
            self.__last_processed_acc_number = context.seq_number

        img_bgr = context.processed_image
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        template_bgr = self.__params.sticker_design
        template_rgb = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2RGB)

        points_list = invariant_match_template(rgbimage=img_rgb, rgbtemplate=template_rgb, method="TM_CCOEFF_NORMED",
                                               matched_thresh=0.5, rot_range=[-15, 15], rot_interval=5,
                                               scale_range=[15, 50], scale_interval=5, rm_redundant=True, minmax=True)

        if len(points_list) > 1:
            raise Exception("more than 2 stickers?")

        # todo различать случай когда наклейка есть, но неверный дизайн
        sticker_present = len(points_list) > 0

        context.validation_results = StickerValidationResult(
            sticker_present=sticker_present,
            sticker_matches_design=sticker_present,
            sticker_image = context.processed_image,
            seq_number=context.seq_number,
        )

        if sticker_present and points_list[0]:
            position_tuple = points_list[0][0]
            rotation = points_list[0][1]
            scale = points_list[0][2]
            confidence = points_list[0][3]
            sticker_width = 0.0
            sticker_height = 0.0
            size_tuple = (float(sticker_width), float(sticker_height))

            context.validation_results.sticker_position=position_tuple
            context.validation_results.sticker_rotation=float(rotation)
            context.validation_results.sticker_size=size_tuple

        self.__last_processed_acc_detections.append(context)

        return context

    # Get result if present and clear it
    def get_combined_validation_result(self) -> StickerValidationResult | None:
        result = self.__combined_validation_result
        self.__combined_validation_result = None
        return result

    def __process_combined_validation(self):
        self.__validation_timer = None

        results = list([context.validation_results for context in self.__last_processed_acc_detections])
        if len(results) == 0:
            return

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

        self.__last_processed_acc_detections = []

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

        self.__combined_validation_result = result
