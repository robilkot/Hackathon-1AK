import logging

import cv2
import time
from dotenv import load_dotenv

from Camera.CameraInterface import CameraInterface
from backend.settings import get_settings

logger = logging.getLogger(__name__)
load_dotenv()

class VideoFileCamera(CameraInterface):
    def __init__(self, settings=None, start_frame=None, start_time=None):
        self.settings = settings or get_settings()
        self.video_path = self.settings.camera.video_path
        self.video_cap = None
        self.is_connected = False
        self._last_frame_time = 0
        self._video_fps = self.settings.processing.fps
        self._frame_duration = None
        self._total_frames = 0
        self._current_frame = 0
        self._start_frame = start_frame
        self._start_time = start_time

        self.__last_debug_time = time.time()
        self.__frames_sent = 0
        self.__debug_interval = 20  # Seconds

    def connect(self, max_retries=3):
        if not self.is_connected:
            retry_count = 0
            while retry_count < max_retries:
                self.video_cap = cv2.VideoCapture(self.video_path)

                if self.video_cap.isOpened():
                    self.is_connected = True
                    self._total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))

                    if self._video_fps is None:
                        self._video_fps = self.video_cap.get(cv2.CAP_PROP_FPS)

                    self._frame_duration = 1.0 / self._video_fps

                    if self._start_frame is not None:
                        self._current_frame = min(self._start_frame, self._total_frames - 1)
                        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame)
                    elif self._start_time is not None:
                        frame_number = int(self._start_time * self._video_fps)
                        self._current_frame = min(frame_number, self._total_frames - 1)
                        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame)

                    self._last_frame_time = time.time()
                    return True

                print(f"Failed to open video file at {self.video_path}. Retrying in 10 seconds...")
                time.sleep(10)
                retry_count += 1

            print(f"Could not open video file after {max_retries} attempts")
            return False
        return True

    def disconnect(self):
        if self.is_connected and self.video_cap:
            self.video_cap.release()
            self.is_connected = False
            return True
        return False

    def get_frame(self):
        if not self.is_connected:
            if not self.connect():
                return None

        current_time = time.time()

        debug_time_diff = current_time - self.__last_debug_time
        if debug_time_diff > self.__debug_interval:
            logger.info(f"read {self.__frames_sent} frames in {self.__debug_interval} ({self.__frames_sent / self.__debug_interval} fps)")
            self.__frames_sent = 0
            self.__last_debug_time = current_time

        # time_diff = current_time - self._last_frame_time
        # frames_to_advance = int(time_diff / self._frame_duration)
        #
        # if frames_to_advance < 1:
        #     return None
        #
        # self._current_frame += frames_to_advance
        #
        # if self._current_frame >= self._total_frames:
        #     self._current_frame = 0
        #     self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        # else:
        #     self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame)

        self._last_frame_time = current_time
        self.__frames_sent += 1

        ret, frame = self.video_cap.read()
        if ret:
            return frame

        self.is_connected = False
        return None


def demo_video_file_camera():
    # Start from frame 100
    #video_camera = VideoFileCamera(start_frame=100)

    # Or start from 30 seconds into the video
    #video_camera = VideoFileCamera(start_time=30.0)
    video_camera = VideoFileCamera()

    if video_camera.connect():
        print("Connected to video file")

        for i in range(10):
            frame = video_camera.get_frame()

            if frame is not None:
                cv2.imshow("Video Frame", frame)
                cv2.waitKey(33)

                time.sleep(0.5)
            else:
                print("No new frame available yet")
                time.sleep(0.1)
        video_camera.disconnect()

        print("Demo complete")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("Failed to connect to video file")


if __name__ == "__main__":
    demo_video_file_camera()