import threading

import cv2
import numpy as np
import urllib.request
import time
from dotenv import load_dotenv

from Camera.CameraInterface import CameraInterface
from backend.settings import get_settings

load_dotenv()

DEFAULT_PHONE_IP = "192.168.1.46"
DEFAULT_PORT = 8080


class IPCamera(CameraInterface):
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.base_url = f"http://{self.settings.camera.phone_ip}:{self.settings.camera.port}"
        self.video_cap = None
        self.is_connected = False
        self.lock = threading.Lock()
        self.t = threading.Thread(target=self._reader)
        self.t.daemon = True
        self.t.start()

    def connect(self, max_retries=3):
        if not self.is_connected:
            video_url = f"{self.base_url}/video"

            retry_count = 0
            while retry_count < max_retries:
                self.video_cap = cv2.VideoCapture(video_url)
                self.video_cap.set(cv2.CAP_PROP_BUFFERSIZE, 0)

                if self.video_cap.isOpened():
                    self.is_connected = True
                    return True

                print(f"Failed to connect to IP Webcam at {video_url}. Retrying in 10 seconds...")
                time.sleep(10)
                retry_count += 1

            print(f"Could not connect to camera after {max_retries} attempts")
            return False
        return True

    def disconnect(self):
        if self.is_connected and self.video_cap:
            self.video_cap.release()
            self.is_connected = False
            return True
        return False

    def get_frame(self):
        with self.lock:
            _, frame = self.video_cap.retrieve()
        return frame

    # grab frames as soon as they are available
    def _reader(self):
        while True:
            if not self.is_connected:
                if not self.connect():
                    continue

            with self.lock:
                ret = self.video_cap.grab()
            if not ret:
                break


def get_video_stream(ip_address=None, port=None, max_retries=3):
    ip_address = ip_address
    port = port
    base_url = f"http://{ip_address}:{port}"
    video_url = f"{base_url}/video"

    retry_count = 0
    while retry_count < max_retries:
        cap = cv2.VideoCapture(video_url)
        if cap.isOpened():
            return cap

        print(f"Failed to connect to IP Webcam at {video_url}. Retrying in 10 seconds...")
        time.sleep(10)
        retry_count += 1

    print(f"Could not connect to camera after {max_retries} attempts")
    return None


def get_frame(cap):
    if cap is None:
        return None

    ret, frame = cap.read()
    if ret:
        return frame
    return None


def get_jpeg_frame(ip_address=None, port=None):
    ip_address = ip_address
    port = port
    base_url = f"http://{ip_address}:{port}"
    shot_url = f"{base_url}/shot.jpg"

    try:
        img_resp = urllib.request.urlopen(shot_url)
        img_np = np.array(bytearray(img_resp.read()), dtype=np.uint8)
        frame = cv2.imdecode(img_np, -1)
        return frame
    except Exception:
        print(f"Failed to get JPEG frame from {shot_url}. Retrying in 10 seconds...")
        time.sleep(10)
        return None


def run_demo():
    print("Demo: IPCamera class")
    camera = IPCamera()

    print("Getting frames using class methods...")
    if camera.connect():
        for i in range(5):
            frame = camera.get_frame()
            if frame is not None:
                cv2.imshow(f'Class Frame {i}', frame)
                cv2.waitKey(33)
        camera.disconnect()

    print("\nDemo: Legacy functions")

    print("Using get_video_stream() and get_frame()...")
    cap = get_video_stream()
    if cap is not None:
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


if __name__ == "__main__":
    run_demo()