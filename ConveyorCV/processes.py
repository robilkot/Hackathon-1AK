import gc
import logging
import multiprocessing
import time
from multiprocessing import Process, Queue
from queue import Empty

from Camera.CameraInterface import CameraInterface
from algorithms.ShapeDetector import ShapeDetector
from algorithms.ShapeProcessor import ShapeProcessor
from algorithms.StickerValidator import StickerValidator, combined_validation_results
from model.model import DetectionContext, StreamingMessage, ImageStreamingMessageContent, \
    ValidationStreamingMessageContent, StreamingMessageType, StickerValidationParams, ContextManagement, IPCMessage, \
    IPCMessageType
from utils.downscale import downscale

logger = logging.getLogger(__name__)


# frames -> BW masks of prop
class ShapeDetectorProcess(Process, ContextManagement):
    def __init__(self, input_queue: Queue, shape_queue: Queue, websocket_queue: Queue, cam: CameraInterface,
                 shape_detector: ShapeDetector,
                 settings, pipe_connection):
        Process.__init__(self, daemon=True)
        self.detector = shape_detector
        self.cam = cam
        self.settings = settings
        self.__shape_queue = shape_queue
        self.__ws_queue = websocket_queue
        self.__frame_count = 0
        self.__input_queue = input_queue
        self.__pipe = pipe_connection
        self.process_name = "detector"

    def get_context(self) -> dict:
        """Return current process context for saving"""
        return {
            "frame_count": self.__frame_count,
        }

    def restore_context(self, context: dict):
        """Restore process context from saved state"""
        if "frame_count" in context:
            pass
            #self.__frame_count = context["frame_count"]

    def __handle_ipc_message(self, message: IPCMessage):
        if message.message_type == IPCMessageType.GET_CONTEXT:
            context_data = self.get_context()
            response = IPCMessage.create_context_response(self.process_name, context_data)
            self.__pipe.send(response)
        elif message.message_type == IPCMessageType.STOP:
            raise InterruptedError("Stop command received")

    def run(self):
        logger.info(f"{self.name} starting")

        self.cam.connect()

        frame_period = 1.0 / self.settings.processing.fps

        while True:
            try:

                if self.__pipe.poll():
                    ipc_message = self.__pipe.recv()
                    if isinstance(ipc_message, IPCMessage) and ipc_message.recipient == self.process_name:
                        self.__handle_ipc_message(ipc_message)
                        continue

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

                image = downscale(image, self.settings.processing.downscale_width,
                                  self.settings.processing.downscale_height)
                context = DetectionContext(image=image)
                context = self.detector.detect(context)

                self.__shape_queue.put_nowait(context)
                self.__ws_queue.put_nowait(
                    StreamingMessage(StreamingMessageType.RAW, ImageStreamingMessageContent(context.image)))

                if context.shape is not None:
                    self.__ws_queue.put_nowait(
                        StreamingMessage(StreamingMessageType.SHAPE, ImageStreamingMessageContent(context.shape)))

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
class ShapeProcessorProcess(Process, ContextManagement):
    def __init__(self, mask_queue: Queue, image_queue: Queue, websocket_queue: Queue, shape_processor: ShapeProcessor,
                 pipe_connection):
        Process.__init__(self, daemon=True)
        self.shape_processor = shape_processor
        self.__mask_queue = mask_queue
        self.__image_queue = image_queue
        self.__ws_queue = websocket_queue
        self.__pipe = pipe_connection
        self.process_name = "processor"

    def get_context(self) -> dict:
        """Return current process context for saving"""
        return {
            "objects_processed": self.shape_processor.objects_processed,
            "last_contour_center_x": self.shape_processor.last_contour_center_x,
            "last_detected_at": self.shape_processor.last_detected_at
        }

    def restore_context(self, context: dict):
        """Restore process context from saved state"""
        if "objects_processed" in context:
            self.shape_processor.objects_processed = context["objects_processed"]
        # if "last_contour_center_x" in context:
        #     self.shape_processor.last_contour_center_x = context["last_contour_center_x"]
        if "last_detected_at" in context:
            self.shape_processor.last_detected_at = context["last_detected_at"]

    def __handle_ipc_message(self, message: IPCMessage):
        if message.message_type == IPCMessageType.GET_CONTEXT:
            context_data = self.get_context()
            response = IPCMessage.create_context_response(self.process_name, context_data)
            self.__pipe.send(response)
        elif message.message_type == IPCMessageType.STOP:
            raise InterruptedError("Stop command received")

    def run(self):
        logger.info(f"{self.name} starting")

        while True:
            try:

                if self.__pipe.poll():
                    ipc_message = self.__pipe.recv()
                    if isinstance(ipc_message, IPCMessage) and ipc_message.recipient == self.process_name:
                        self.__handle_ipc_message(ipc_message)
                        continue

                context = self.__mask_queue.get()

                if context is None:
                    raise InterruptedError

                context = self.shape_processor.process(context)

                if context.processed_image is not None:
                    self.__image_queue.put_nowait(context)
                    self.__ws_queue.put_nowait(StreamingMessage(StreamingMessageType.PROCESSED,
                                                                ImageStreamingMessageContent(context.processed_image)))


            except (KeyboardInterrupt, InterruptedError):
                logger.info(f"{self.name} exiting")
                return
            except Exception as e:
                logger.error(f"{self.name} exception: ", e)


# aligned and cropped images -> validation results for prop
class StickerValidatorProcess(Process, ContextManagement):
    def __init__(self, image_queue: Queue, validation_results_queue: Queue, websocket_queue: Queue,
                 validator: StickerValidator, pipe_connection):
        Process.__init__(self, daemon=True)
        self.validator = validator
        self.__input_queue = image_queue
        self.__results_queue = validation_results_queue
        self.__ws_queue = websocket_queue
        self.__pipe = pipe_connection
        self.process_name = "validator"

    def get_context(self) -> dict:
        """Return current process context for saving"""
        return {
            "last_processed_acc_number": self.validator._StickerValidator__last_processed_acc_number,
            "validation_parameters": self.validator.get_parameters()
        }

    def restore_context(self, context: dict):
        """Restore process context from saved state"""
        if "last_processed_acc_number" in context:
            self.validator._StickerValidator__last_processed_acc_number = context["last_processed_acc_number"]
        if "validation_parameters" in context and context["validation_parameters"]:
            self.validator.set_parameters(context["validation_parameters"])

    def set_validator_parameters(self, params: StickerValidationParams):
        logger.info(f"Set validator parameters: {params}")
        self.validator.set_parameters(params)

    def get_validator_parameters(self) -> StickerValidationParams:
        return self.validator.get_parameters()

    def __handle_ipc_message(self, message: IPCMessage):
        if message.message_type == IPCMessageType.GET_CONTEXT:
            context = self.get_context()
            self.__pipe.send(IPCMessage.create_context_response("validator", context))

        elif message.message_type == IPCMessageType.PARAMS:
            if message.content["action"] == "get":
                params = self.get_validator_parameters()
                self.__pipe.send(IPCMessage(IPCMessageType.PARAMS, "validator", params.to_dict()))

            elif message.content["action"] == "set":
                params_dict = message.content["params"]
                sticker_params = StickerValidationParams.from_dict(params_dict)
                self.set_validator_parameters(sticker_params)
                self.__pipe.send(IPCMessage(IPCMessageType.PARAMS, "validator", {"status": "success"}))

        elif message.message_type == IPCMessageType.STOP:
            raise InterruptedError("Stop command received")

    def run(self):
        logger.info(f"{self.name} starting")

        while True:
            try:

                if self.__pipe.poll():
                    ipc_message = self.__pipe.recv()
                    if isinstance(ipc_message, IPCMessage) and ipc_message.recipient == self.process_name:
                        self.__handle_ipc_message(ipc_message)
                        continue

                try:
                    context = self.__input_queue.get(timeout=1)

                    if context is None:
                        raise InterruptedError

                    _ = self.validator.validate(context)
                except Empty:
                    self.validator.process_combined_validation()

                try:
                    combined_result = combined_validation_results.get_nowait()
                    self.__results_queue.put_nowait(combined_result)
                    self.__ws_queue.put_nowait(StreamingMessage(StreamingMessageType.VALIDATION,
                                                                ValidationStreamingMessageContent(combined_result)))
                except Empty:
                    pass
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
                # logger.info("get context from results queue: %s", context)
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
