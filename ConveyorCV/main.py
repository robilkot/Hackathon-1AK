from Camera.IPCamera import IPCamera
from Camera.VideoFileCamera import VideoFileCamera
from Contour.ContourDetector import ContourDetector

cd = ContourDetector()
# cam = IPCamera()
cam = VideoFileCamera()
cd.draw_contours(cam)
