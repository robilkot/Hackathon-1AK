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
            center=sticker_params.center,
            sticker_size=sticker_params.sticker_size,
            battery_size=sticker_params.battery_size,
            rotation=sticker_params.rotation
        )

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
        sticker_location = points_list[0] if sticker_present else None
        context.validation_results = ValidationResults(sticker_present, sticker_present, sticker_location)

        return context