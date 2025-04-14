import cv2
import numpy as np
import urllib.request
import time


class IPCamera:
    def __init__(self, ip_address=None, port=None):
        from config import PHONE_IP, PORT

        self.ip_address = ip_address or PHONE_IP
        self.port = port or PORT
        self.base_url = f"http://{self.ip_address}:{self.port}"
        self.video_cap = None
        self.is_connected = False

    def connect(self):
        if not self.is_connected:
            video_url = f"{self.base_url}/video"
            self.video_cap = cv2.VideoCapture(video_url)

            if not self.video_cap.isOpened():
                raise ConnectionError(f"Failed to connect to IP Webcam at {video_url}")

            self.is_connected = True
            return True
        return False

    def disconnect(self):
        if self.is_connected and self.video_cap:
            self.video_cap.release()
            self.is_connected = False
            return True
        return False

    def get_frame(self):
        if not self.is_connected:
            self.connect()

        ret, frame = self.video_cap.read()
        if ret:
            return frame
        return None

    def get_jpeg_frame(self):
        shot_url = f"{self.base_url}/shot.jpg"
        img_resp = urllib.request.urlopen(shot_url)
        img_np = np.array(bytearray(img_resp.read()), dtype=np.uint8)
        frame = cv2.imdecode(img_np, -1)
        return frame

    def capture_frames(self, num_frames=30, fps=30, use_stream=True):
        frames = []
        delay = 1.0 / fps

        if use_stream and not self.is_connected:
            self.connect()

        for _ in range(num_frames):
            start_time = time.time()

            if use_stream:
                frame = self.get_frame()
            else:
                frame = self.get_jpeg_frame()

            if frame is not None:
                frames.append(frame)

            processing_time = time.time() - start_time
            if processing_time < delay:
                time.sleep(delay - processing_time)

        return frames


def get_video_stream(ip_address=None, port=None):
    from config import PHONE_IP, PORT
    ip_address = ip_address or PHONE_IP
    port = port or PORT
    base_url = f"http://{ip_address}:{port}"
    video_url = f"{base_url}/video"
    cap = cv2.VideoCapture(video_url)
    if not cap.isOpened():
        raise ConnectionError(f"Failed to connect to IP Webcam at {video_url}")
    return cap


def get_frame(cap):
    ret, frame = cap.read()
    if ret:
        return frame
    return None


def get_jpeg_frame(ip_address=None, port=None):
    from config import PHONE_IP, PORT
    ip_address = ip_address or PHONE_IP
    port = port or PORT
    base_url = f"http://{ip_address}:{port}"
    shot_url = f"{base_url}/shot.jpg"
    img_resp = urllib.request.urlopen(shot_url)
    img_np = np.array(bytearray(img_resp.read()), dtype=np.uint8)
    frame = cv2.imdecode(img_np, -1)
    return frame


if __name__ == "__main__":
    print("Demo: IPCamera class")
    camera = IPCamera()

    print("Getting frames using class methods...")
    camera.connect()
    for i in range(5):
        frame = camera.get_frame()
        if frame is not None:
            cv2.imshow(f'Class Frame {i}', frame)
            cv2.waitKey(33)
    camera.disconnect()

    print("Getting batch of frames...")
    frames = camera.capture_frames(num_frames=3, fps=10)
    for i, frame in enumerate(frames):
        cv2.imshow(f'Batch Frame {i}', frame)
        cv2.waitKey(500)

    print("\nDemo: Legacy functions")

    print("Using get_video_stream() and get_frame()...")
    cap = get_video_stream()
    for i in range(3):
        frame = get_frame(cap)
        if frame is not None:
            cv2.imshow(f'Legacy Stream Frame {i}', frame)
            cv2.waitKey(33)
    cap.release()

    print("Using get_jpeg_frame()...")
    for i in range(3):
        frame = get_jpeg_frame()
        if frame is not None:
            cv2.imshow(f'Legacy JPEG Frame {i}', frame)
            cv2.waitKey(500)
            time.sleep(0.5)

    print("Demo complete. Press any key to close windows.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()