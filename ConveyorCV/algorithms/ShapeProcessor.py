from datetime import datetime

from backend.settings import get_settings
import cv2
import numpy as np

from model.model import DetectionContext


class ShapeProcessor:
    def __init__(self, settings=None, initial_counter=0):
        self.settings = settings or get_settings()
        self.objects_processed = initial_counter
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

    def __filter_shadow_points(self, contour, image_height):
        """Filter contour points to reduce shadow effects"""
        # Define top and bottom 5% regions
        top_region_height = int(image_height * 0.05)
        bottom_region_height = int(image_height * 0.95)

        # Separate points into regions
        top_points = []
        bottom_points = []
        middle_points = []

        for point in contour:
            x, y = point[0]
            if y < top_region_height:
                top_points.append(point)
            elif y > bottom_region_height:
                bottom_points.append(point)
            else:
                middle_points.append(point)

        # Find leftmost and rightmost points in each region
        filtered_points = []

        # For top region
        if top_points:
            leftmost_top = min(top_points, key=lambda p: p[0][0])
            rightmost_top = max(top_points, key=lambda p: p[0][0])
            filtered_points.extend([leftmost_top, rightmost_top])

        # For bottom region
        if bottom_points:
            leftmost_bottom = min(bottom_points, key=lambda p: p[0][0])
            rightmost_bottom = max(bottom_points, key=lambda p: p[0][0])
            filtered_points.extend([leftmost_bottom, rightmost_bottom])

        # Include some middle points to maintain shape
        filtered_points.extend(middle_points)

        return np.array(filtered_points)

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
        (y, x, _) = context.image.shape
        contours, _ = cv2.findContours(shape, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        border_left = self.settings.detection.detection_border_left
        border_right = self.settings.detection.detection_border_right
        line_height = self.settings.detection.detection_line_height

        p1 = (x * border_left, y * line_height)
        p2 = (x * border_right, y * line_height)

        for c in contours:
            # Filter shadow points first
            filtered_contour = self.__filter_shadow_points(c, y)

            epsilon = 0.05 * cv2.arcLength(filtered_contour, True)
            corners = cv2.approxPolyDP(filtered_contour, epsilon, True)

            bool_fits = True
            if bool_fits:
                bool_fits = bool_fits & (cv2.pointPolygonTest(corners, p1, False) > 0)
            if bool_fits:
                bool_fits = bool_fits & (cv2.pointPolygonTest(corners, p2, False) > 0)
            if bool_fits:
                processed_image = self.__cut_out_contour_evened_out(image_source, corners)
                context.processed_image = processed_image
                context.processed_image_corners = corners
                self.__on_contour_valid(context, c)
                break

        return context
