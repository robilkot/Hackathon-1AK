import multiprocessing
from multiprocessing import Queue

import cv2

from Camera.CameraInterface import CameraInterface
from Camera.VideoFileCamera import VideoFileCamera
from algorithms.ShapeDetector import ShapeDetector
from algorithms.ShapeProcessor import ShapeProcessor
from algorithms.StickerValidator import StickerValidator
from model.model import DetectionContext, ValidationParams
from utils.downscale import downscale
from utils.env import DOWNSCALE_WIDTH, DOWNSCALE_HEIGHT


# frames -> BW masks of prop
class ShapeDetectorProcess(multiprocessing.Process):
    def __init__(self, input_queue: Queue, cam: CameraInterface, shape_detector: ShapeDetector):
        multiprocessing.Process.__init__(self)
        self.__shape_queue = input_queue
        self.__cam = cam
        self.__detector = shape_detector

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
            except Exception as e:
                print(f"{self.name} exception: ", e)


# BW masks of prop -> aligned and cropped images
class ShapeProcessorProcess(multiprocessing.Process):
    def __init__(self, mask_queue: Queue, image_queue: Queue, shape_processor: ShapeProcessor):
        multiprocessing.Process.__init__(self)
        self.__mask_queue = mask_queue
        self.__image_queue = image_queue
        self.__shape_processor = shape_processor

    def run(self):
        while True:
            try:
                context = self.__mask_queue.get()
                context = self.__shape_processor.process(context)

                if context.processed_image is not None:
                    self.__image_queue.put(context)
            except Exception as e:
                print(f"{self.name} exception: ", e)


# aligned and cropped images -> validation results for prop
class StickerValidatorProcess(multiprocessing.Process):
    def __init__(self, image_queue: Queue, validation_results_queue: Queue, validator: StickerValidator):
        multiprocessing.Process.__init__(self)
        self.__validator = validator
        self.__input_queue = image_queue
        self.__results_queue = validation_results_queue

    def run(self):
        while True:
            try:
                context = self.__input_queue.get()
                context = self.__validator.validate(context)
                self.__results_queue.put(context)
            except Exception as e:
                print(f"{self.name} exception: ", e)


# Final step of pipeline to show data
class DisplayerProcess(multiprocessing.Process):
    def __init__(self, results: Queue):
        multiprocessing.Process.__init__(self)
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
            cv2.imshow(f'result {i}', context.processed_image)

            if cv2.waitKey(5) & 0xFF == ord("q"):
                break
        return


if __name__ == '__main__':
    sticker_validator_params = ValidationParams(cv2.imread('data/sticker_fixed.png'))

    shape_queue = multiprocessing.Queue()
    processed_shape_queue = multiprocessing.Queue()
    results_queue = multiprocessing.Queue()
    # test_input = multiprocessing.Queue()

    shape_detector = ShapeDetectorProcess(shape_queue, VideoFileCamera(), ShapeDetector())
    shape_processor = ShapeProcessorProcess(shape_queue, results_queue, ShapeProcessor())
    sticker_validator = StickerValidatorProcess(processed_shape_queue, results_queue, StickerValidator(sticker_validator_params))

    displayer = DisplayerProcess(results_queue)

    shape_detector.start()
    shape_processor.start()
    # sticker_validator.start()
    displayer.start()

    # inp = [DetectionContext(None, processed_image=cv2.imread(f'data/{path}.png')) for path in ["test_acc1", "test_acc2", "test_acc3", "test_acc1_3deg", "test_acc1_5deg", "test_acc1_10deg"]]
    # for i in inp:
    #     test_input.put(i)

    displayer.join()
    shape_detector.terminate()
    shape_processor.terminate()
    sticker_validator.terminate()
