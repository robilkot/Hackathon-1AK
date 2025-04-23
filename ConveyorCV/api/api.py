import asyncio
import base64
import time
from pathlib import Path
import os

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, UploadFile, File, HTTPException, BackgroundTasks
import cv2
import threading
import multiprocessing
from multiprocessing import Queue
import json

from websocket_manager import WebSocketManager, StreamType
from settings import Settings, get_settings, update_settings
from fastapi.responses import HTMLResponse

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

# Event queue for sending detection events
event_queue = Queue()

# Processes
shape_detector_process = None
shape_processor_process = None
sticker_validator_process = None

# Flag to control streaming
is_streaming = False
streaming_task = None

# Ensure data directories exist
UPLOAD_DIR = Path("data/uploads")
STICKER_DIR = Path("data/stickers")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STICKER_DIR, exist_ok=True)


def initialize_processes(settings: Settings):
    global shape_queue, processed_shape_queue, results_queue, event_queue
    global shape_detector_process, shape_processor_process, sticker_validator_process

    # Initialize queues
    shape_queue = multiprocessing.Queue()
    processed_shape_queue = multiprocessing.Queue()
    results_queue = multiprocessing.Queue()
    event_queue = multiprocessing.Queue()

    # Select camera based on settings
    camera: CameraInterface
    if settings.camera_type == "video":
        camera = VideoFileCamera(settings.camera.video_path)
    else:  # "ip"
        camera = IPCamera(settings.camera.phone_ip, settings.camera.port)

    #todo delete if this is bullshit
    sticker_design = cv2.imread(settings.sticker_design_path)
    sticker_validator_params = ValidationParams(
        sticker_design=sticker_design,
        center=(sticker_design.shape[1] // 2, sticker_design.shape[0] // 2),
        size=(sticker_design.shape[1], sticker_design.shape[0]),
        rotation=0.0
    )

    # Initialize processes
    shape_detector_process = ShapeDetectorProcess(
        shape_queue, camera, ShapeDetector())

    shape_processor_process = ShapeProcessorProcess(
        shape_queue, processed_shape_queue, ShapeProcessor())

    sticker_validator_process = StickerValidatorProcess(
        processed_shape_queue, results_queue, StickerValidator(sticker_validator_params))


# Modify the validation results handling in stream_images_async
async def stream_images_async():
    global is_streaming, shape_queue, processed_shape_queue, results_queue

    while is_streaming:
        # Process raw frames
        if not shape_queue.empty():
            context = shape_queue.get()
            await manager.broadcast_image(context.image, StreamType.RAW)

            if context.shape is not None:
                shape_img = cv2.cvtColor(context.shape, cv2.COLOR_GRAY2BGR)
                await manager.broadcast_image(shape_img, StreamType.SHAPE)

        # Process detected shapes
        if not processed_shape_queue.empty():
            context = processed_shape_queue.get()
            if context.processed_image is not None:
                await manager.broadcast_image(context.processed_image, StreamType.PROCESSED)

                # Send object detection event
                event_data = {
                    "type": "object_detected",
                    "timestamp": time.time(),
                    "seq_number": context.seq_number
                }
                if StreamType.EVENTS in manager.active_connections:
                    for connection in manager.active_connections[StreamType.EVENTS]:
                        await connection.send_json(event_data)

        # Process validation results
        if not results_queue.empty():
            context = results_queue.get()
            if context.processed_image is not None and context.validation_results is not None:
                # Send validation event with all details
                validation_results = context.validation_results
                event_data = {
                    "type": "validation_result",
                    "timestamp": time.time(),
                    "seq_number": context.seq_number,
                    "sticker_present": validation_results.sticker_present,
                    "sticker_matches_design": validation_results.sticker_matches_design,
                    "image": None,  # Will be set below if needed
                }

                # Optionally include the processed image in base64 format
                if context.processed_image is not None:
                    _, encoded_img = cv2.imencode('.jpg', context.processed_image)
                    base64_img = base64.b64encode(encoded_img.tobytes()).decode('utf-8')
                    event_data["image"] = base64_img

                # Send to all event websocket connections
                if StreamType.EVENTS in manager.active_connections:
                    for connection in manager.active_connections[StreamType.EVENTS]:
                        await connection.send_json(event_data)

        await asyncio.sleep(0.033)  # ~30fps


def start_streaming():
    global is_streaming, shape_detector_process, shape_processor_process, sticker_validator_process

    if not is_streaming:
        # Re-initialize processes if needed
        settings = get_settings()
        initialize_processes(settings)

        shape_detector_process.start()
        shape_processor_process.start()
        sticker_validator_process.start()
        is_streaming = True


def stop_streaming():
    global is_streaming, shape_detector_process, shape_processor_process, sticker_validator_process

    if is_streaming:
        is_streaming = False

        # Terminate processes
        if shape_detector_process and shape_detector_process.is_alive():
            shape_detector_process.terminate()
        if shape_processor_process and shape_processor_process.is_alive():
            shape_processor_process.terminate()
        if sticker_validator_process and sticker_validator_process.is_alive():
            sticker_validator_process.terminate()

        # Re-initialize for next time
        settings = get_settings()
        initialize_processes(settings)


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


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for detection events and notifications"""
    await websocket.accept()
    manager.active_connections.setdefault(StreamType.EVENTS, []).append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        if StreamType.EVENTS in manager.active_connections:
            if websocket in manager.active_connections[StreamType.EVENTS]:
                manager.active_connections[StreamType.EVENTS].remove(websocket)


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
async def start_stream_endpoint(background_tasks: BackgroundTasks):
    global is_streaming, streaming_task

    if not is_streaming:
        # Initialize processes
        settings = get_settings()
        initialize_processes(settings)

        shape_detector_process.start()
        shape_processor_process.start()
        sticker_validator_process.start()
        is_streaming = True

        background_tasks.add_task(stream_images_async)

    return {"status": "streaming started"}


@app.post("/stream/stop")
async def stop_stream():
    stop_streaming()
    return {"status": "streaming stopped"}


@app.post("/upload/sticker")
async def upload_sticker(file: UploadFile = File(...)):
    """Upload a new sticker design"""
    if not file.filename.endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(400, detail="Only PNG and JPG images are allowed")

    # Save the file
    file_path = STICKER_DIR / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Update the settings to use the new sticker
    settings = get_settings()
    was_streaming = is_streaming

    if was_streaming:
        stop_streaming()

    settings.sticker_design_path = str(file_path)
    updated_settings = update_settings(settings)

    # Reinitialize with new sticker
    initialize_processes(updated_settings)

    if was_streaming:
        start_streaming()

    return {"status": "success", "file_path": str(file_path)}


@app.post("/sticker/parameters")
async def set_sticker_parameters(sticker_params: dict):
    """Set sticker parameters for validation"""
    global sticker_validator_process

    # Decode base64 image
    image_bytes = base64.b64decode(sticker_params["image"])
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    # Create StickerParameters object
    params = ValidationParams(
        sticker_design=image,
        center=(float(sticker_params["centerX"]), float(sticker_params["centerY"])),
        size=(float(sticker_params["width"]), float(sticker_params["height"])),
        rotation=float(sticker_params["rotation"])
    )

    # Update sticker validator parameters
    was_streaming = is_streaming
    if was_streaming:
        stop_streaming()

    # We need to update the validator and restart
    sticker_validator_process.terminate()
    sticker_validator = StickerValidator()
    sticker_validator.set_parameters(params)
    sticker_validator_process = StickerValidatorProcess(
        processed_shape_queue, results_queue, sticker_validator)

    if was_streaming:
        start_streaming()

    return {"status": "success", "message": "Sticker parameters updated"}


@app.get("/example", response_class=HTMLResponse)
def get_example_html():
    """Return example HTML page for testing the streaming and WebSocket API"""
    return """
    <!DOCTYPE html>
<html>
<head>
    <title>ConveyorCV Stream Viewer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .stream { margin-bottom: 20px; }
        img { max-width: 100%; border: 1px solid #ccc; }
        #events { height: 300px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; }
        #validationResults { border: 1px solid #ccc; padding: 10px; margin-bottom: 20px; }
        .valid { background-color: #d4edda; color: #155724; }
        .invalid { background-color: #f8d7da; color: #721c24; }
        button { margin: 5px; padding: 8px 16px; }
    </style>
</head>
<body>
    <h1>ConveyorCV Stream Viewer</h1>
    <div>
        <button id="startBtn">Start Streaming</button>
        <button id="stopBtn">Stop Streaming</button>
        <input type="file" id="stickerUpload" accept=".jpg,.jpeg,.png">
        <button id="uploadBtn">Upload Sticker</button>
    </div>
    <div class="grid">
        <div class="stream">
            <h2>Raw Stream</h2>
            <img id="rawStream" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==">
        </div>
        <div class="stream">
            <h2>Shape Detection</h2>
            <img id="shapeStream" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==">
        </div>
        <div class="stream">
            <h2>Processed Objects</h2>
            <img id="processedStream" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==">
        </div>
        <div>
            <h2>Latest Validation</h2>
            <div id="validationResults">Waiting for validation results...</div>
            <img id="validationImage" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==">
        </div>
    </div>
    <h2>Detection Events</h2>
    <div id="events"></div>

    <script>
        const host = window.location.host;

        // Stream WebSockets
        const rawWs = new WebSocket(`ws://${host}/ws/raw`);
        const shapeWs = new WebSocket(`ws://${host}/ws/shape`);
        const processedWs = new WebSocket(`ws://${host}/ws/processed`);
        const eventsWs = new WebSocket(`ws://${host}/ws/events`);

        // Images
        const rawImg = document.getElementById('rawStream');
        const shapeImg = document.getElementById('shapeStream');
        const processedImg = document.getElementById('processedStream');
        const validationImg = document.getElementById('validationImage');
        const validationResults = document.getElementById('validationResults');
        const eventsDiv = document.getElementById('events');

        // Process received messages
        rawWs.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.image) rawImg.src = 'data:image/jpeg;base64,' + data.image;
        };

        shapeWs.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.image) shapeImg.src = 'data:image/jpeg;base64,' + data.image;
        };

        processedWs.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.image) processedImg.src = 'data:image/jpeg;base64,' + data.image;
        };

        eventsWs.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const timestamp = new Date(data.timestamp * 1000).toLocaleTimeString();
            let message = '';

            if (data.type === 'object_detected') {
                message = `[${timestamp}] Object detected: #${data.seq_number}`;
            } else if (data.type === 'validation_result') {
                message = `[${timestamp}] Validation #${data.seq_number}: Sticker present: ${data.sticker_present}, Matches design: ${data.sticker_matches_design}`;
                
                // Update validation results div
                validationResults.textContent = `Object #${data.seq_number}: ${data.sticker_present ? 'Sticker present' : 'No sticker'}, ${data.sticker_matches_design ? 'Valid design' : 'Invalid design'}`;
                validationResults.className = data.sticker_matches_design ? 'valid' : 'invalid';
                
                // Update validation image if available
                if (data.image) {
                    validationImg.src = 'data:image/jpeg;base64,' + data.image;
                }
            }

            if (message) {
                const div = document.createElement('div');
                div.textContent = message;
                eventsDiv.appendChild(div);
                eventsDiv.scrollTop = eventsDiv.scrollHeight;
            }
        };

        // Button handlers
        document.getElementById('startBtn').addEventListener('click', async () => {
            const response = await fetch('/stream/start', { method: 'POST' });
            const result = await response.json();
            console.log(result);
        });

        document.getElementById('stopBtn').addEventListener('click', async () => {
            const response = await fetch('/stream/stop', { method: 'POST' });
            const result = await response.json();
            console.log(result);
        });

        document.getElementById('uploadBtn').addEventListener('click', async () => {
            const fileInput = document.getElementById('stickerUpload');
            if (!fileInput.files.length) {
                alert('Please select a file first');
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            const response = await fetch('/upload/sticker', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            console.log(result);
            alert(`Sticker uploaded: ${result.file_path}`);
        });
    </script>
</body>
</html>
    """