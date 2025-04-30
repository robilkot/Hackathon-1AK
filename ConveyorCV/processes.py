import gc
import logging
import multiprocessing
import time
from multiprocessing import Process, Queue
from queue import Empty
from warnings import catch_warnings

import cv2

from Camera.CameraInterface import CameraInterface
from algorithms.ShapeDetector import ShapeDetector
from algorithms.ShapeProcessor import ShapeProcessor
from algorithms.StickerValidator import StickerValidator
from model.model import DetectionContext, StreamingMessage, ImageStreamingMessageContent, \
    ValidationStreamingMessageContent, StreamingMessageType, StickerValidationParams
from utils.downscale import downscale
from utils.env import DOWNSCALE_WIDTH, DOWNSCALE_HEIGHT

logger = logging.getLogger(__name__)


# frames -> BW masks of prop
class ShapeDetectorProcess(Process):
    def __init__(self, input_queue: Queue, shape_queue: Queue, websocket_queue: Queue, cam: CameraInterface, shape_detector: ShapeDetector,
                 fps: int):
        Process.__init__(self, daemon=True)
        self.detector = shape_detector
        self.cam = cam
        self.fps = fps
        self.__shape_queue = shape_queue
        self.__ws_queue = websocket_queue
        self.__frame_count = 0
        self.__input_queue = input_queue

    def run(self):
        logger.info(f"{self.name} starting")

        self.cam.connect()

        frame_period = 1.0 / self.fps

        while True:
            try:
                try:
                    stop = self.__input_queue.get_nowait()
                    if stop is None:
                        raise InterruptedError
                except Empty:
                    pass

                start_time = time.time()

                image = self.cam.get_frame()
                if image is None:
                    continue

                self.__frame_count += 1

                image = downscale(image, DOWNSCALE_WIDTH, DOWNSCALE_HEIGHT)
                context = DetectionContext(image=image)
                context = self.detector.detect(context)

                self.__shape_queue.put_nowait(context)
                self.__ws_queue.put_nowait(StreamingMessage(StreamingMessageType.RAW, ImageStreamingMessageContent(context.image)))

                if context.shape is not None:
                    self.__ws_queue.put_nowait(StreamingMessage(StreamingMessageType.SHAPE, ImageStreamingMessageContent(context.shape)))

                if self.__frame_count % 200 == 0:
                    gc.collect()

                elapsed_time = time.time() - start_time
                # print(elapsed_time)

                if elapsed_time < frame_period:
                    time.sleep(frame_period - elapsed_time)

            except (KeyboardInterrupt, InterruptedError):
                logger.info(f"{self.name} exiting")
                return
            except Exception as e:
                logger.error(f"{self.name} exception: ", e)


# BW masks of prop -> aligned and cropped images
class ShapeProcessorProcess(Process):
    def __init__(self, mask_queue: Queue, image_queue: Queue, websocket_queue: Queue, shape_processor: ShapeProcessor):
        Process.__init__(self, daemon=True)
        self.shape_processor = shape_processor
        self.__mask_queue = mask_queue
        self.__image_queue = image_queue
        self.__ws_queue = websocket_queue

    def run(self):
        logger.info(f"{self.name} starting")

        while True:
            try:
                context = self.__mask_queue.get()

                if context is None:
                    raise InterruptedError

                context = self.shape_processor.process(context)

                if context.processed_image is not None:
                    self.__image_queue.put_nowait(context)
                    self.__ws_queue.put_nowait(StreamingMessage(StreamingMessageType.PROCESSED, ImageStreamingMessageContent(context.processed_image)))


            except (KeyboardInterrupt, InterruptedError):
                logger.info(f"{self.name} exiting")
                return
            except Exception as e:
                logger.error(f"{self.name} exception: ", e)


# aligned and cropped images -> validation results for prop
class StickerValidatorProcess(Process):
    def __init__(self, image_queue: Queue, validation_results_queue: Queue, websocket_queue: Queue, validator: StickerValidator):
        Process.__init__(self, daemon=True)
        self.validator = validator
        self.__input_queue = image_queue
        self.__results_queue = validation_results_queue
        self.__ws_queue = websocket_queue

    def set_validator_parameters(self, params: StickerValidationParams):
        logger.info(f"Set validator parameters: {params}")
        self.validator.set_parameters(params)

    def get_validator_parameters(self) -> StickerValidationParams:
        return self.validator.get_parameters()

    def run(self):
        logger.info(f"{self.name} starting")

        while True:
            try:
                try:
                    context = self.__input_queue.get(timeout=1)

                    if context is None:
                        raise InterruptedError

                    _ = self.validator.validate(context)
                except Empty:
                    pass

                combined_result = self.validator.get_combined_validation_result()

                if combined_result is not None:
                    self.__results_queue.put_nowait(combined_result)
                    self.__ws_queue.put_nowait(StreamingMessage(StreamingMessageType.VALIDATION, ValidationStreamingMessageContent(combined_result)))
            except (KeyboardInterrupt, InterruptedError):
                logger.info(f"{self.name} exiting")
                return
            except Exception as e:
                logger.error(f"{self.name} exception: ", e)


class ValidationResultsLogger(Process):
    def __init__(self, results_queue: Queue):
        Process.__init__(self, daemon=True)
        self.__results_queue = results_queue
        self.session = None

    def initialize_db(self):
        from backend.db import get_db_session
        self.session = get_db_session()

    def run(self):
        logger.info(f"{self.name} starting")
        self.initialize_db()

        while True:
            try:
                validation_results = self.__results_queue.get()
                #logger.info("get context from results queue: %s", context)
                if validation_results is None:
                    raise InterruptedError

                if validation_results is not None:
                    from model.model import ValidationLog

                    validation_log = ValidationLog(
                        timestamp=validation_results.detected_at,
                        seq_number=validation_results.seq_number,
                        sticker_present=validation_results.sticker_present,
                        sticker_matches_design=validation_results.sticker_matches_design,
                        sticker_position_x=validation_results.sticker_position[
                            0] if validation_results.sticker_position else None,
                        sticker_position_y=validation_results.sticker_position[
                            1] if validation_results.sticker_position else None,
                        sticker_size_width=validation_results.sticker_size[
                            0] if validation_results.sticker_size else None,
                        sticker_size_height=validation_results.sticker_size[
                            1] if validation_results.sticker_size else None,
                        sticker_rotation=validation_results.sticker_rotation
                    )

                    self.session.add(validation_log)
                    self.session.commit()

            except (KeyboardInterrupt, InterruptedError):
                logger.info(f"{self.name} exiting")
                if self.session:
                    self.session.close()
                return
            except Exception as e:
                logger.error(f"{self.name} exception: {str(e)}")
                if self.session:
                    self.session.rollback()
