from abc import ABC, abstractmethod

class CameraInterface(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def get_frame(self):
        pass

    def create_camera_from_config(config):
        """Creates a camera instance based on configuration"""
        camera_type = config.get("type", "video")

        if camera_type == "video":
            from Camera.VideoFileCamera import VideoFileCamera
            return VideoFileCamera(config.get("video_path", "data/cropped.mp4"))
        elif camera_type == "ip":
            from Camera.IPCamera import IPCamera
            return IPCamera(
                config.get("ip", "192.168.1.46"),
                config.get("port", "8080")
            )
        else:
            raise ValueError(f"Unsupported camera type: {camera_type}")