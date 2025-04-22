import asyncio
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
import cv2
import threading
import multiprocessing
from multiprocessing import Queue

from websocket_manager import WebSocketManager, StreamType
from settings import Settings, get_settings, update_settings

from Camera.CameraInterface import CameraInterface
from Camera.VideoFileCamera import VideoFileCamera
from Camera.IPCamera import IPCamera
from algorithms.ShapeDetector import ShapeDetector
from algorithms.ShapeProcessor import ShapeProcessor
from algorithms.StickerValidator import StickerValidator
from main import ShapeDetectorProcess, ShapeProcessorProcess, StickerValidatorProcess
from model.model import DetectionContext, ValidationParams
from utils.downscale import downscale

# Initialize FastAPI app
app = FastAPI(title="Conveyor CV API")

# Initialize WebSocket manager
manager = WebSocketManager()

# Queues for communication between processes
shape_queue = None
processed_shape_queue = None
results_queue = None

# Processes
shape_detector_process = None
shape_processor_process = None
sticker_validator_process = None

# Flag to control streaming
is_streaming = False


def initialize_processes(settings: Settings):
    global shape_queue, processed_shape_queue, results_queue
    global shape_detector_process, shape_processor_process, sticker_validator_process

    # Initialize queues
    shape_queue = multiprocessing.Queue()
    processed_shape_queue = multiprocessing.Queue()
    results_queue = multiprocessing.Queue()

    # Select camera based on settings
    camera: CameraInterface
    if settings.camera_type == "video":
        camera = VideoFileCamera(settings.camera.video_path)
    else:  # "ip"
        camera = IPCamera(settings.camera.phone_ip, settings.camera.port)

    # Load sticker design from settings
    sticker_validator_params = ValidationParams(cv2.imread(settings.sticker_design_path))

    # Initialize processes
    shape_detector_process = ShapeDetectorProcess(
        shape_queue, camera, ShapeDetector())

    shape_processor_process = ShapeProcessorProcess(
        shape_queue, processed_shape_queue, ShapeProcessor())

    sticker_validator_process = StickerValidatorProcess(
        processed_shape_queue, results_queue, StickerValidator(sticker_validator_params))


def start_streaming():
    global is_streaming, shape_detector_process, shape_processor_process, sticker_validator_process

    if not is_streaming:
        shape_detector_process.start()
        shape_processor_process.start()
        sticker_validator_process.start()
        is_streaming = True
        threading.Thread(target=stream_images, daemon=True).start()


def stop_streaming():
    global is_streaming, shape_detector_process, shape_processor_process, sticker_validator_process

    if is_streaming:
        is_streaming = False
        shape_detector_process.terminate()
        shape_processor_process.terminate()
        sticker_validator_process.terminate()


def stream_images():
    global is_streaming, shape_queue, processed_shape_queue, results_queue

    while is_streaming:
        # Try to get from shape_queue for raw shapes
        if not shape_queue.empty():
            context = shape_queue.get()
            if context.image is not None:
                asyncio.run(manager.broadcast_image(context.image, StreamType.RAW))
            if context.shape is not None:
                # Convert BW to BGR for display
                shape_colored = cv2.cvtColor(context.shape, cv2.COLOR_GRAY2BGR)
                asyncio.run(manager.broadcast_image(shape_colored, StreamType.SHAPE))

        # Try to get from processed_shape_queue for processed shapes
        if not processed_shape_queue.empty():
            context = processed_shape_queue.get()
            if context.processed_image is not None:
                asyncio.run(manager.broadcast_image(context.processed_image, StreamType.PROCESSED))

        # Try to get from results_queue for validation results
        if not results_queue.empty():
            context = results_queue.get()
            if context.processed_image is not None:
                # Draw validation results on the image
                img_with_results = context.processed_image.copy()
                if context.validation_results is not None:
                    # Add text with validation results
                    text = f"Sticker Present: {context.validation_results.sticker_present}"
                    cv2.putText(img_with_results, text, (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                    if context.validation_results.sticker_position is not None:
                        # Mark the sticker position
                        point = context.validation_results.sticker_position[0]
                        cv2.circle(img_with_results, point, 10, (0, 0, 255), -1)

                asyncio.run(manager.broadcast_image(img_with_results, StreamType.VALIDATION))

        time.sleep(0.033)  # ~30fps


@app.on_event("startup")
async def startup_event():
    settings = get_settings()
    initialize_processes(settings)


@app.on_event("shutdown")
async def shutdown_event():
    stop_streaming()


@app.websocket("/ws/raw")
async def websocket_raw(websocket: WebSocket):
    await manager.connect(websocket, StreamType.RAW)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket, StreamType.RAW)


@app.websocket("/ws/shape")
async def websocket_shape(websocket: WebSocket):
    await manager.connect(websocket, StreamType.SHAPE)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket, StreamType.SHAPE)


@app.websocket("/ws/processed")
async def websocket_processed(websocket: WebSocket):
    await manager.connect(websocket, StreamType.PROCESSED)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket, StreamType.PROCESSED)


@app.websocket("/ws/validation")
async def websocket_validation(websocket: WebSocket):
    await manager.connect(websocket, StreamType.VALIDATION)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket, StreamType.VALIDATION)


@app.get("/settings", response_model=Settings)
async def get_current_settings():
    return get_settings()


@app.post("/settings", response_model=Settings)
async def update_current_settings(settings: Settings):
    was_streaming = is_streaming
    if was_streaming:
        stop_streaming()

    # Update the settings
    updated = update_settings(settings)

    # Reinitialize processes with new settings
    initialize_processes(updated)

    if was_streaming:
        start_streaming()

    return updated


@app.post("/stream/start")
async def start_stream():
    start_streaming()
    return {"status": "streaming started"}


@app.post("/stream/stop")
async def stop_stream():
    stop_streaming()
    return {"status": "streaming stopped"}