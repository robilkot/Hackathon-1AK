import cv2


def downscale(img, width, height):
    down_points = (width, height)
    return cv2.resize(img, down_points, interpolation=cv2.INTER_LINEAR)