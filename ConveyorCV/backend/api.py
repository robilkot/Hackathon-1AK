import asyncio
import base64
import datetime
from multiprocessing import Queue, Process

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse

from Camera.CameraInterface import CameraInterface
from Camera.IPCamera import IPCamera
from Camera.VideoFileCamera import VideoFileCamera
from algorithms.ShapeDetector import ShapeDetector
from algorithms.ShapeProcessor import ShapeProcessor
from algorithms.StickerValidator import StickerValidator
from model.model import ValidationParams, StreamingMessage
from processes import ShapeDetectorProcess, ShapeProcessorProcess, StickerValidatorProcess
from settings import Settings, get_settings, update_settings
from websocket_manager import WebSocketManager

app = FastAPI(title="Conveyor CV API")
settings = get_settings()

manager = WebSocketManager()
shape_queue = Queue()
processed_shape_queue = Queue()
results_queue = Queue()
websocket_queue = Queue()

camera: CameraInterface
if settings.camera_type == "video":
    camera = VideoFileCamera(settings.camera.video_path)
else:
    camera = IPCamera(settings.camera.phone_ip, settings.camera.port)

#todo delete if this is bullshit
sticker_design = cv2.imread(settings.sticker_design_path)
if sticker_design is None:
    raise Exception("sticker_design not found")

#todo make it correct
sticker_validator_params = ValidationParams(
    sticker_design=sticker_design,
    sticker_center=(50.0, 50.0),  # Default center point
    acc_size=(200.0, 200.0),    # Default acceptable size
    sticker_size=(100.0, 100.0),  # Default sticker size
    sticker_rotation=0.0        # Default rotation angle
)

detector = ShapeDetector()
processor = ShapeProcessor()
validator = StickerValidator(sticker_validator_params)
shape_detector_process: Process = ShapeDetectorProcess(shape_queue, websocket_queue, camera, detector, 20)
shape_processor_process = ShapeProcessorProcess(shape_queue, processed_shape_queue, websocket_queue, processor)
sticker_validator_process = StickerValidatorProcess(processed_shape_queue, results_queue, websocket_queue, validator)


async def stream_images_async():
    last_time = datetime.datetime.now()
    while True:
        try:
            msg: StreamingMessage = websocket_queue.get()

            await manager.broadcast_message(msg)
        except Exception as e:
            print(f"exception: ", e)
            raise e

        current_time = datetime.datetime.now()
        if current_time - last_time > datetime.timedelta(seconds=2):
            last_time = current_time
            print('shape_queue: ', shape_queue.qsize())
            print('processed_shape_queue: ', processed_shape_queue.qsize())
            print('results_queue: ', results_queue.qsize())
            print('websocket_queue: ', websocket_queue.qsize())
        await asyncio.sleep(0.033)  # ~30fps


def start_processes():
    shape_detector_process.start()
    shape_processor_process.start()
    sticker_validator_process.start()
    print("Processes started")

def stop_processes():
    # todo shitty impl
    shape_detector_process.terminate()
    shape_processor_process.terminate()
    sticker_validator_process.terminate()


@app.websocket("/ws")
async def websocket_connect(websocket: WebSocket):
    try:
        await manager.connect(websocket)
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect as e:
        manager.disconnect(websocket)
        raise e


@app.get("/settings", response_model=Settings)
async def get_current_settings():
    return get_settings()


@app.post("/settings", response_model=Settings)
async def update_current_settings(settings: Settings):
    updated = update_settings(settings)

    # todo

    return updated

@app.post("/stream/start")
async def start_stream_endpoint(background_tasks: BackgroundTasks):
    start_processes()
    background_tasks.add_task(stream_images_async)
    return {"status": "streaming started"}


@app.post("/stream/stop")
async def stop_stream():
    stop_processes()
    return {"status": "streaming stopped"}

#todo create endpoint to get validator params
@app.get("/sticker/parameters")
async def get_sticker_parameters():
    params = validator.get_parameters()
    return params.to_dict()

@app.post("/sticker/parameters")
async def set_sticker_parameters(sticker_params: dict):
    global sticker_validator_process

    # Decode base64 image
    image_bytes = base64.b64decode(sticker_params["image"])
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    print("Sticker params: ",sticker_params)
    # Create StickerParameters object
    params = ValidationParams(
        sticker_design=image,
        sticker_center=(float(sticker_params["centerX"]), float(sticker_params["centerY"])),
        sticker_size=(float(sticker_params["width"]), float(sticker_params["height"])),
        sticker_rotation=float(sticker_params["rotation"]),
    )

    # We need to update the validator and restart
    sticker_validator_process.terminate()
    validator = StickerValidator(params)
    sticker_validator_process = StickerValidatorProcess(processed_shape_queue, results_queue, websocket_queue, validator)

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