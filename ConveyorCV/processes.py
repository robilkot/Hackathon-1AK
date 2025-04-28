import gc
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
    ValidationStreamingMessageContent, StreamingMessageType
from utils.downscale import downscale
from utils.env import DOWNSCALE_WIDTH, DOWNSCALE_HEIGHT


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
        print(f"{self.name} starting")

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
                print(f"{self.name} exiting")
                return
            except Exception as e:
                print(f"{self.name} exception: ", e)


# BW masks of prop -> aligned and cropped images
class ShapeProcessorProcess(Process):
    def __init__(self, mask_queue: Queue, image_queue: Queue, websocket_queue: Queue, shape_processor: ShapeProcessor):
        Process.__init__(self, daemon=True)
        self.shape_processor = shape_processor
        self.__mask_queue = mask_queue
        self.__image_queue = image_queue
        self.__ws_queue = websocket_queue

    def run(self):
        print(f"{self.name} starting")

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
                print(f"{self.name} exiting")
                return
            except Exception as e:
                print(f"{self.name} exception: ", e)


# aligned and cropped images -> validation results for prop
class StickerValidatorProcess(Process):
    def __init__(self, image_queue: Queue, validation_results_queue: Queue, websocket_queue: Queue, validator: StickerValidator):
        Process.__init__(self, daemon=True)
        self.validator = validator
        self.__input_queue = image_queue
        self.__results_queue = validation_results_queue
        self.__ws_queue = websocket_queue

    def run(self):
        print(f"{self.name} starting")

        while True:
            try:
                context = self.__input_queue.get()

                if context is None:
                    raise InterruptedError

                context = self.validator.validate(context)
                self.__results_queue.put_nowait(context)

                if context.validation_results is not None:
                    self.__ws_queue.put_nowait(StreamingMessage(StreamingMessageType.VALIDATION, ValidationStreamingMessageContent(context.validation_results)))

            except (KeyboardInterrupt, InterruptedError):
                print(f"{self.name} exiting")
                return
            except Exception as e:
                print(f"{self.name} exception: ", e)


# Final step of pipeline to show data
# class DisplayerProcess(BaseProcess):
#     def __init__(self, results: Queue):
#         Process.__init__(self)
#         self.__results = results
#
#     def run(self):
#         context = None
#         i = 0
#         while True:
#             if not self.__results.empty():
#                 context = self.__results.get()
#                 i += 1
#
#             if context is None:
#                 if i != 0:
#                     print('why')
#                 continue
#
#             # print(context.validation_results)
#             # cv2.imshow(f'result {i}', context.processed_image)
#
#             if cv2.waitKey(5) & 0xFF == ord("q"):
#                 break
#         return
