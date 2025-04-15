from ConveyorCV.Camera.IPCamera import IPCamera
from ConveyorCV.Camera.VideoFileCamera import VideoFileCamera
from ConveyorCV.Contour.ContourDetector import ContourDetector

cd = ContourDetector()
cam = VideoFileCamera()
cd.draw_contours(cam)