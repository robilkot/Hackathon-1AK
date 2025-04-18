import cv2
import numpy as np


def downscale(img, width, height):
    down_points = (width, height)
    return cv2.resize(img, down_points, interpolation=cv2.INTER_LINEAR)


# todo: бенчмарк, надо реалтайм (20 фпс хотя бы, 30 - идеал)
class ContourDetector:
    @staticmethod
    def draw_contours(cam):
        cam.connect()

        width, height = 1280, 720

        # todo: четко определить размер ядра
        kernel = np.ones((12, 12), np.uint8)
        image_conveyor_empty = cv2.imread('data/frame_empty.png')
        image_conveyor_empty = downscale(image_conveyor_empty, width, height)
        image_conveyor_empty = cv2.morphologyEx(image_conveyor_empty, cv2.MORPH_CLOSE, kernel, iterations=3)

        while True:
            try:
                image = cam.get_frame()
                if image is None:
                    continue

                image = downscale(image, width, height)
                image_source = image.copy()

                image = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel, iterations=3)

                image_diff = cv2.absdiff(image, image_conveyor_empty)
                image_gray = cv2.cvtColor(image_diff, cv2.COLOR_BGR2GRAY)

                # todo: четко определить порог
                _, image_thresh = cv2.threshold(image_gray, 50, 255, cv2.THRESH_BINARY)
                image_eroded = cv2.erode(image_thresh, None, iterations=7)
                image_dilated = cv2.dilate(image_eroded, None, iterations=7)

                # todo: четко определить размер ядра
                image_dilated_kernel = np.ones((15, 15), np.uint8)
                image_dilated = cv2.morphologyEx(image_dilated, cv2.MORPH_CLOSE, image_dilated_kernel, iterations=7)

                display = cv2.addWeighted(cv2.cvtColor(image_dilated, cv2.COLOR_GRAY2RGB), 0.7, image_source, 1, 0)
                cv2.imshow('result', display)

                if cv2.waitKey(5) & 0xFF == ord("q"):
                    break

            except Exception as e:
                print("Exception: ", e)

        cv2.destroyAllWindows()
