import asyncio
import base64
import datetime
import logging
import multiprocessing
import queue
from contextlib import asynccontextmanager
from multiprocessing import Queue, Process
from queue import Empty

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


# todo start/stop processes in production (with IP camera) here
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    # ...

    yield

    # shutdown
    # ...

app = FastAPI(title="Conveyor CV API", lifespan=lifespan)

settings = get_settings()

manager = WebSocketManager()

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


exit_queue: Queue
shape_queue: Queue
processed_shape_queue: Queue
results_queue: Queue
websocket_queue: Queue
shape_detector_process: Process
shape_processor_process: Process
sticker_validator_process: Process
processes: list
queues: list

def init_processes():
    global shape_detector_process, shape_processor_process, sticker_validator_process, processes
    global exit_queue, shape_queue, processed_shape_queue, websocket_queue, results_queue, queues

    exit_queue = Queue()
    shape_queue = Queue()
    processed_shape_queue = Queue()
    results_queue = Queue()
    websocket_queue = Queue()

    shape_detector_process = ShapeDetectorProcess(exit_queue, shape_queue, websocket_queue, camera, detector, 20)
    shape_processor_process = ShapeProcessorProcess(shape_queue, processed_shape_queue, websocket_queue, processor)
    sticker_validator_process = StickerValidatorProcess(processed_shape_queue, results_queue, websocket_queue, validator)

    processes = [shape_detector_process, shape_processor_process, sticker_validator_process]
    queues = [exit_queue, shape_queue, processed_shape_queue, results_queue, websocket_queue]

init_processes()

async def stream_images_async():
    print(f"stream_images_async starting")
    last_time = datetime.datetime.now()
    while True:
        try:
            msg: StreamingMessage = websocket_queue.get_nowait()

            if msg is None:
                raise InterruptedError

            await manager.broadcast_message(msg)
        except queue.Empty:
            pass
        except (KeyboardInterrupt, InterruptedError):
            print(f"stream_images_async exiting")
            return
        except Exception as e:
            print(f"stream_images_async exception: ", str(e), type(e))

        current_time = datetime.datetime.now()
        if current_time - last_time > datetime.timedelta(seconds=2):
            last_time = current_time
            # print('shape_queue: ', shape_queue.qsize())
            # print('processed_shape_queue: ', processed_shape_queue.qsize())
            # print('results_queue: ', results_queue.qsize())
            # print('websocket_queue: ', websocket_queue.qsize())
        await asyncio.sleep(0.033)  # ~30fps


def start_processes(background_tasks: BackgroundTasks):
    init_processes()

    for process in processes:
        if not process.is_alive():
            process.start()

    background_tasks.add_task(stream_images_async)


def stop_processes():
    for queue in queues:
        while not queue.empty():
            queue.get()

        queue.put(None)


@app.websocket("/ws")
async def websocket_connect(websocket: WebSocket):
    try:
        await manager.connect(websocket)
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect as e:
        manager.disconnect(websocket)
        if e.code != 1000:
            logging.warn(f'websocket closed: code {e.code}')


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
    start_processes(background_tasks)
    return {"status": "streaming started"}


@app.post("/stream/stop")
async def stop_stream():
    stop_processes()
    return {"status": "streaming stopped"}

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

    # Create StickerParameters object - now with acc_size
    params = ValidationParams(
        sticker_design=image,
        sticker_center=(float(sticker_params["centerX"]), float(sticker_params["centerY"])),
        sticker_size=(float(sticker_params["width"]), float(sticker_params["height"])),
        acc_size=(float(sticker_params.get("accWidth", 200)), float(sticker_params.get("accHeight", 200))),  # Added missing parameter
        sticker_rotation=float(sticker_params["rotation"]),
    )

    # Update the validator and restart
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
        <button id="getParamsBtn">Get Sticker Parameters</button>
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
        </div>
    </div>
    <h2>Detection Events</h2>
    <div id="events"></div>

    <script>
        const host = window.location.host;
        let ws = null;

        // Message types
        const TYPE_RAW = 1;
        const TYPE_SHAPE = 2;
        const TYPE_PROCESSED = 3;
        const TYPE_VALIDATION = 4;

        // Connect to WebSocket
        function connectWebSocket() {
            ws = new WebSocket(`ws://${host}/ws`);

            ws.onopen = () => {
                console.log('WebSocket connected');
                addEvent('WebSocket connected');
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
                addEvent('WebSocket disconnected');
                // Attempt to reconnect after a delay
                setTimeout(connectWebSocket, 2000);
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                addEvent('WebSocket error: ' + error);
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    const type = message.type;
                    const contentObj = JSON.parse(message.content);

                    switch (type) {
                        case TYPE_RAW:
                            document.getElementById('rawStream').src = 'data:image/jpeg;base64,' + contentObj.image;
                            break;

                        case TYPE_SHAPE:
                            document.getElementById('shapeStream').src = 'data:image/jpeg;base64,' + contentObj.image;
                            break;

                        case TYPE_PROCESSED:
                            document.getElementById('processedStream').src = 'data:image/jpeg;base64,' + contentObj.image;
                            break;

                        case TYPE_VALIDATION:
                            handleValidationResult(contentObj.validation_result);
                            break;

                        default:
                            console.log('Unknown message type:', type);
                    }
                } catch (e) {
                    console.error('Error parsing message:', e);
                    console.error('Raw message:', event.data);
                }
            };
        }

        function handleValidationResult(result) {
            const validationResults = document.getElementById('validationResults');

            const stickerPresent = result.sticker_present;
            const stickerMatchesDesign = result.sticker_matches_design;
            const seqNumber = result.seq_number;

            validationResults.textContent = `Object #${seqNumber}: ${stickerPresent ? 'Sticker present' : 'No sticker'}, ${stickerMatchesDesign ? 'Valid design' : 'Invalid design'}`;
            validationResults.className = stickerMatchesDesign ? 'valid' : 'invalid';

            addEvent(`[${new Date().toLocaleTimeString()}] Validation #${seqNumber}: Sticker present: ${stickerPresent}, Matches design: ${stickerMatchesDesign}`);
        }

        function addEvent(message) {
            const div = document.createElement('div');
            div.textContent = message;
            document.getElementById('events').appendChild(div);
            document.getElementById('events').scrollTop = document.getElementById('events').scrollHeight;
        }

        // Initialize WebSocket connection
        connectWebSocket();

        // Button handlers
        document.getElementById('startBtn').addEventListener('click', async () => {
            try {
                const response = await fetch('/stream/start', { method: 'POST' });
                const result = await response.json();
                console.log(result);
                addEvent(`Stream started: ${JSON.stringify(result)}`);
            } catch (e) {
                console.error('Error starting stream:', e);
                addEvent(`Error starting stream: ${e.message}`);
            }
        });

        document.getElementById('stopBtn').addEventListener('click', async () => {
            try {
                const response = await fetch('/stream/stop', { method: 'POST' });
                const result = await response.json();
                console.log(result);
                addEvent(`Stream stopped: ${JSON.stringify(result)}`);
            } catch (e) {
                console.error('Error stopping stream:', e);
                addEvent(`Error stopping stream: ${e.message}`);
            }
        });

        document.getElementById('getParamsBtn').addEventListener('click', async () => {
            try {
                const response = await fetch('/sticker/parameters');
                const result = await response.json();
                console.log(result);
                addEvent(`Sticker parameters: ${JSON.stringify(result)}`);
            } catch (e) {
                console.error('Error getting parameters:', e);
                addEvent(`Error getting parameters: ${e.message}`);
            }
        });
    </script>
</body>
</html>
    """