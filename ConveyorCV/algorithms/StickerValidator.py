from datetime import datetime

import cv2

from algorithms.InvariantTM import invariant_match_template
from model.model import ValidationParams, DetectionContext, ValidationResults


class StickerValidator:
    def __init__(self, params: ValidationParams):
        self.__params = params
        assert(self.__params.sticker_design is not None)

    def set_parameters(self, sticker_params: ValidationParams):
        """Set the validation parameters for the sticker validator"""
        self.__params = ValidationParams(
            sticker_design=sticker_params.sticker_design,
            sticker_center=sticker_params.sticker_center,
            sticker_size=sticker_params.sticker_size,
            sticker_rotation=sticker_params.sticker_rotation,
            acc_size= sticker_params.acc_size
        )

    def get_parameters(self) -> ValidationParams:
        """Get the current validation parameters from the sticker validator"""
        return self.__params

    def validate(self, context: DetectionContext) -> DetectionContext:
        assert(context.processed_image is not None)

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
        if sticker_present and points_list[0]:
            position_tuple = points_list[0][0]
            rotation = points_list[0][1]
            scale = points_list[0][2]
            confidence = points_list[0][3]
            sticker_width = None
            sticker_height = None
            size_tuple = (float(sticker_width), float(sticker_height))

            context.validation_results = ValidationResults(
                sticker_present=sticker_present,
                sticker_matches_design=sticker_present,
                sticker_position=position_tuple,
                sticker_rotation=float(rotation),
                sticker_size=size_tuple,
                seq_number=context.seq_number if hasattr(context, 'seq_number') else 0,
                timestamp=datetime.now()
            )
        else:
            context.validation_results = ValidationResults(
                sticker_present=False,
                sticker_matches_design=False
            )

        return context