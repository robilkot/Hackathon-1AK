import cv2
import numpy as np

def downscale(img):
    down_width = 1280
    down_height = 720
    down_points = (down_width, down_height)
    return cv2.resize(img, down_points, interpolation=cv2.INTER_LINEAR)

def dense_optical_flow(method, video_path, params=[], to_gray=False):
    # read the video
    cap = cv2.VideoCapture(video_path)
    # Read the first frame
    ret, old_frame = cap.read()
    old_frame = downscale(old_frame)

    # crate HSV & make Value a constant
    hsv = np.zeros_like(old_frame)
    hsv[..., 1] = 255

    # Preprocessing for exact method
    if to_gray:
        old_frame = cv2.cvtColor(old_frame, cv2.COLOR_BGR2GRAY)

    while True:
        # Read the next frame
        ret, new_frame = cap.read()
        new_frame = downscale(new_frame)

        frame_copy = new_frame
        if not ret:
            break


        # Preprocessing for exact method
        if to_gray:
            new_frame = cv2.cvtColor(new_frame, cv2.COLOR_BGR2GRAY)
        # Calculate Optical Flow
        # flow = cv2.calcOpticalFlowFarneback(old_frame, new_frame, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        flow = cv2.calcOpticalFlowFarneback(old_frame, new_frame, None, 0.5, 3, 15, 3, 5, 1.2, 0)

        # Encoding: convert the algorithm's output into Polar coordinates
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        # Use Hue and Saturation to encode the Optical Flow
        hsv[..., 0] = ang * 180 / np.pi / 2
        hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
        # Convert HSV image into BGR for demo
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        cv2.imshow("frame", frame_copy)
        cv2.imshow("optical flow", bgr)
        k = cv2.waitKey(5) & 0xFF
        if k == ord("q"):
            break
        old_frame = new_frame