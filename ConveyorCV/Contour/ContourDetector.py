import cv2
import numpy as np
import datetime
from PIL import Image
from ConveyorCV.utils.env import *


def downscale(img, width, height):
    down_points = (width, height)
    return cv2.resize(img, down_points, interpolation=cv2.INTER_LINEAR)


# todo: бенчмарк, надо реалтайм (20 фпс хотя бы, 30 - идеал)
class ContourDetector:


    def order_points(self, pts):
        '''Rearrange coordinates to order:
          top-left, top-right, bottom-right, bottom-left'''
        rect = np.zeros((4, 2), dtype='float32')
        pts = np.array(pts)
        s = pts.sum(axis=1)
        # Top-left point will have the smallest sum.
        rect[0] = pts[np.argmin(s)]
        # Bottom-right point will have the largest sum.
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        # Top-right point will have the smallest difference.
        rect[1] = pts[np.argmin(diff)]
        # Bottom-left will have the largest difference.
        rect[3] = pts[np.argmax(diff)]
        # Return the ordered coordinates.
        return rect.astype('int').tolist()

    def find_dest(self, pts):
        (tl, tr, br, bl) = pts
        # Finding the maximum width.
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))

        # Finding the maximum height.
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        # Final destination co-ordinates.
        destination_corners = [[0, 0], [maxWidth, 0], [maxWidth, maxHeight], [0, maxHeight]]

        return self.order_points(destination_corners)

    def draw_contours(self, cam):
        cam.connect()

        width, height = 1280, 720
        i = 1

        # todo: четко определить размер ядра
        kernel = np.ones((12, 12), np.uint8)
        image_conveyor_empty = cv2.imread(BG_PHOTO_PATH)
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
                image_blurred = cv2.GaussianBlur(image_gray, (11, 11), 0)

                # todo: четко определить порог
                _, image_thresh = cv2.threshold(image_blurred, 50, 255, cv2.THRESH_BINARY)
                image_eroded = cv2.erode(image_thresh, None, iterations=7)
                canny = cv2.Canny(image_eroded, 0, 200)
                image_dilated = cv2.dilate(canny, None, iterations=7)
                #image_dilated = cv2.dilate(canny, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

                # todo: четко определить размер ядра
                image_dilated_kernel = np.ones((15, 15), np.uint8)
                image_dilated = cv2.morphologyEx(image_dilated, cv2.MORPH_CLOSE, image_dilated_kernel, iterations=7)

                # Finding contours for the detected edges.
                contours, hierarchy = cv2.findContours(image_dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
                display = cv2.addWeighted(cv2.cvtColor(image_dilated, cv2.COLOR_GRAY2RGB), 0.7, image_source, 1, 0)

                for c in contours:
                    epsilon = 0.05 * cv2.arcLength(c, True)
                    corners = cv2.approxPolyDP(c, epsilon, True)

                    bool_fits = True
                    if bool_fits:
                        bool_fits = bool_fits & (cv2.pointPolygonTest(corners, (440, 360), False) > 0)
                    if bool_fits:
                        bool_fits = bool_fits & (cv2.pointPolygonTest(corners, (840, 360), False) > 0)
                    if bool_fits:

                        #cv2.drawContours(display, c, -1, (0, 0, 255), 5)
                        #cv2.drawContours(display, corners, -1, (255, 0, 255), 5)

                        if i == 1000:
                            i = 1

                        filename = OUT_CAPTURES_NAME
                        filename = filename.format(when=datetime.datetime.now(), n=i)
                        i = i + 1

                        # Sorting the corners and converting them to desired shape.
                        corners = sorted(np.concatenate(corners).tolist())
                        # For 4 corner points being detected.
                        corners = self.order_points(corners)

                        destination_corners = self.find_dest(corners)
                        h, w = display.shape[:2]
                        # Getting the homography.
                        M = cv2.getPerspectiveTransform(np.float32(corners), np.float32(destination_corners))
                        # Perspective transform using homography.
                        final = cv2.warpPerspective(image_source, M, (destination_corners[2][0], destination_corners[2][1]),
                                                    flags=cv2.INTER_LINEAR)

                        im = Image.fromarray(final)
                        im.save(OUT_CAPTURES_PATH + filename, format='png')

                #cv2.imshow('result', image_source)

                if cv2.waitKey(5) & 0xFF == ord("q"):
                    break

            except Exception as e:
                print("Exception: ", e)

        cv2.destroyAllWindows()
