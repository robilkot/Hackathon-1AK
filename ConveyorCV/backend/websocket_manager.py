import time
from typing import Dict, List
import asyncio
from fastapi import WebSocket
import base64
import cv2
import numpy as np
from enum import Enum, auto


last_broadcast_time = {}

class StreamType(Enum):
    RAW = auto()
    SHAPE = auto()
    PROCESSED = auto()
    VALIDATION = auto()
    EVENTS = auto()

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[StreamType, List[WebSocket]] = {
            stream_type: [] for stream_type in StreamType
        }
        self.latest_images: Dict[StreamType, np.ndarray] = {}

    async def connect(self, websocket: WebSocket, stream_type: StreamType):
        await websocket.accept()
        if self.active_connections.get(stream_type, None) is None:
            self.active_connections[stream_type] = []
        self.active_connections[stream_type].append(websocket)

        # Send the latest image if available
        if stream_type in self.latest_images and self.latest_images[stream_type] is not None:
            await self.send_image(websocket, self.latest_images[stream_type])

    def disconnect(self, websocket: WebSocket, stream_type: StreamType):
        self.active_connections[stream_type].remove(websocket)

    @staticmethod
    async def send_image(websocket: WebSocket, image: np.ndarray):
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 75]
        _, encoded_img = cv2.imencode('.jpg', image, encode_params)
        base64_img = base64.b64encode(encoded_img.tobytes()).decode('utf-8')
        await websocket.send_json({"image": base64_img})

    async def broadcast_image(self, image: np.ndarray, stream_type: StreamType):
        current_time = time.time()
        if stream_type in last_broadcast_time and current_time - last_broadcast_time[stream_type] < 0.1:
            return

        last_broadcast_time[stream_type] = current_time
        self.latest_images[stream_type] = image
        for connection in self.active_connections[stream_type]:
            try:
                await self.send_image(connection, image)
            except Exception:
                # Remove dead connections
                await connection.close()
                self.active_connections[stream_type].remove(connection)