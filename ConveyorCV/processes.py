# frames -> BW masks of prop
import base64
import time
import cv2

from Camera.CameraInterface import CameraInterface
from algorithms.ShapeDetector import ShapeDetector
from algorithms.ShapeProcessor import ShapeProcessor
from algorithms.StickerValidator import StickerValidator
from backend.websocket_manager import WebSocketManager, StreamType
from model.model import DetectionContext, StreamingContext
from utils.downscale import downscale
from utils.env import DOWNSCALE_WIDTH, DOWNSCALE_HEIGHT
from multiprocess import Process, Queue


class ShapeDetectorProcess(Process):
    def __init__(self, input_queue: Queue, websocket_queue: Queue, cam: CameraInterface, shape_detector: ShapeDetector):
        Process.__init__(self)
        self.__shape_queue = input_queue
        self.__cam = cam
        self.__detector = shape_detector
        self.__ws_queue = websocket_queue

    def run(self):
        self.__cam.connect()

        while True:
            try:
                image = self.__cam.get_frame()
                if image is None:
                    continue
                image = downscale(image, DOWNSCALE_WIDTH, DOWNSCALE_HEIGHT)
                context = DetectionContext(image=image)
                context = self.__detector.detect(context)
                self.__shape_queue.put(context)

                self.__ws_queue.put(StreamingContext(context.image, StreamType.RAW))

                if context.shape is not None:
                    self.__ws_queue.put(StreamingContext(context.shape, StreamType.SHAPE))
            except Exception as e:
                print(f"{self.name} exception: ", e)


# BW masks of prop -> aligned and cropped images
class ShapeProcessorProcess(Process):
    def __init__(self, mask_queue: Queue, image_queue: Queue, websocket_queue: Queue, shape_processor: ShapeProcessor):
        Process.__init__(self)
        self.__mask_queue = mask_queue
        self.__image_queue = image_queue
        self.__shape_processor = shape_processor
        self.__ws_queue = websocket_queue

    def run(self):
        while True:
            try:
                context = self.__mask_queue.get()
                context = self.__shape_processor.process(context)

                if context.processed_image is not None:
                    self.__image_queue.put(context)
                    self.__ws_queue.put(StreamingContext(context.processed_image, StreamType.PROCESSED))

                    event_data = {
                        "type": "object_detected",
                        "timestamp": time.time(),
                        "seq_number": context.seq_number
                    }
                    self.__ws_queue.put(StreamingContext(event_data, StreamType.EVENTS))
            except Exception as e:
                print(f"{self.name} exception: ", e)


# aligned and cropped images -> validation results for prop
class StickerValidatorProcess(Process):
    def __init__(self, image_queue: Queue, validation_results_queue: Queue, websocket_queue: Queue, validator: StickerValidator):
        Process.__init__(self)
        self.__validator = validator
        self.__input_queue = image_queue
        self.__results_queue = validation_results_queue
        self.__ws_queue = websocket_queue

    def run(self):
        while True:
            try:
                context = self.__input_queue.get()
                context = self.__validator.validate(context)
                self.__results_queue.put(context)

                event_data = {
                    "type": "validation_result",
                    "timestamp": time.time(),
                    "seq_number": context.seq_number,
                    "sticker_present": context.validation_results.sticker_present,
                    "sticker_matches_design": context.validation_results.sticker_matches_design,
                    "image": None,  # Will be set below if needed
                }

                _, encoded_img = cv2.imencode('.jpg', context.processed_image)
                base64_img = base64.b64encode(encoded_img.tobytes()).decode('utf-8')
                event_data["image"] = base64_img

                self.__ws_queue.put(StreamingContext(event_data, StreamType.EVENTS))
            except Exception as e:
                print(f"{self.name} exception: ", e)


# Final step of pipeline to show data
class DisplayerProcess(Process):
    def __init__(self, results: Queue):
        Process.__init__(self)
        self.__results = results

    def run(self):
        context = None
        i = 0
        while True:
            if not self.__results.empty():
                context = self.__results.get()
                i += 1

            if context is None:
                if i != 0:
                    print('why')
                continue

            # print(context.validation_results)
            # cv2.imshow(f'result {i}', context.processed_image)

            if cv2.waitKey(5) & 0xFF == ord("q"):
                break
        return
