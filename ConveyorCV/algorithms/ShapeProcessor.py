from datetime import datetime

import cv2
import numpy as np

from model.model import DetectionContext


class ShapeProcessor:
    def __init__(self):
        self.objects_processed = 0
        self.last_contour_center_x = 0
        self.last_detected_at = datetime.now()

    def __on_contour_valid(self, context, contour):
        now = datetime.now()
        M = cv2.moments(contour)
        if M['m00'] != 0:
            cx = int(M['m10'] / M['m00'])
#            cy = int(M['m01'] / M['m00'])
        else:
            cx = 0
#            cy = 0


        if self.last_contour_center_x < cx:
            self.objects_processed = self.objects_processed + 1

        self.last_contour_center_x = cx
        self.last_detected_at = now

        #gcontext.center_x = cx
        context.seq_number  = self.objects_processed
        context.detected_at = self.last_detected_at

    def __order_points(self, pts):
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

    def __find_dest(self, pts):
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

        return self.__order_points(destination_corners)

    def __cut_out_contour_evened_out(self, image, corners):
        corners = sorted(np.concatenate(corners).tolist())
        corners = self.__order_points(corners)
        destination_corners = self.__find_dest(corners)
        m = cv2.getPerspectiveTransform(np.float32(corners), np.float32(destination_corners))
        return cv2.warpPerspective(image, m, (destination_corners[2][0], destination_corners[2][1]), flags=cv2.INTER_LINEAR)

    def process(self, context: DetectionContext) -> DetectionContext:
        image_source = context.image
        shape = context.shape
        (y, x, Null) = context.image.shape
        contours, hierarchy = cv2.findContours(shape, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        for c in contours:
            epsilon = 0.05 * cv2.arcLength(c, True)
            corners = cv2.approxPolyDP(c, epsilon, True)

            bool_fits = True
            if bool_fits:
                bool_fits = bool_fits & (cv2.pointPolygonTest(corners, (0.4*x, 0.5*y), False) > 0)
            if bool_fits:
                bool_fits = bool_fits & (cv2.pointPolygonTest(corners, (0.6*x, 0.5*y), False) > 0)
            if bool_fits:
                processed_image = self.__cut_out_contour_evened_out(image_source, corners)
                context.processed_image = processed_image
                self.__on_contour_valid(context, c)
                break

        return context
