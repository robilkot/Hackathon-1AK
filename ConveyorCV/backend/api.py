import asyncio
import datetime
import logging
import queue
import time
from contextlib import asynccontextmanager
from multiprocessing import Queue, Pipe
from fastapi import Query, APIRouter
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse
from starlette.middleware.cors import CORSMiddleware

from Camera.CameraInterface import CameraInterface
from Camera.IPCamera import IPCamera
from Camera.VideoFileCamera import VideoFileCamera
from algorithms.ShapeDetector import ShapeDetector
from algorithms.ShapeProcessor import ShapeProcessor
from algorithms.StickerValidator import StickerValidator
from backend.context_manager import ContextManager
from backend.db import paginate_validation_logs, delete_validation_log_by_id, delete_all_validation_logs
from model.model import StickerValidationParams, StreamingMessage, StreamingMessageType
from processes import ShapeDetectorProcess, ShapeProcessorProcess, StickerValidatorProcess, ValidationResultsLogger
from settings import get_settings, Settings, save_settings
from utils.bg_capture import save_and_set_empty_conveyor_background
from utils.param_persistence import save_sticker_parameters
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

# Configure CORS middleware
origins = [
    "https://localhost:7169",  # WASM app origin
    "http://localhost:5235",  # WASM app origin
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

settings = get_settings()

manager = WebSocketManager()
context_manager = ContextManager()

camera: CameraInterface
if settings.camera_type == "video":
    camera = VideoFileCamera(settings.camera.video_path)
else:
    camera = IPCamera(settings.camera.phone_ip, settings.camera.port)

detector = ShapeDetector()
processor = ShapeProcessor()
validator = StickerValidator()

exit_queue: Queue
shape_queue: Queue
processed_shape_queue: Queue
results_queue: Queue
websocket_queue: Queue
ipc_queue: Queue

detector_parent_pipe = None
detector_child_pipe = None
processor_parent_pipe = None
processor_child_pipe = None
validator_parent_pipe = None
validator_child_pipe = None

shape_detector_process: ShapeDetectorProcess
shape_processor_process: ShapeProcessorProcess
sticker_validator_process: StickerValidatorProcess
validation_logger_process: ValidationResultsLogger
processes: list
queues: list


def init_processes():
    global shape_detector_process, shape_processor_process, sticker_validator_process, validation_logger_process, processes
    global exit_queue, shape_queue, processed_shape_queue, websocket_queue, results_queue, queues
    global detector_parent_pipe, detector_child_pipe, processor_parent_pipe, processor_child_pipe, validator_parent_pipe, validator_child_pipe
    exit_queue = Queue()
    shape_queue = Queue()
    processed_shape_queue = Queue()
    results_queue = Queue()
    websocket_queue = Queue()

    detector_parent_pipe, detector_child_pipe = Pipe()
    processor_parent_pipe, processor_child_pipe = Pipe()
    validator_parent_pipe, validator_child_pipe = Pipe()

    shape_detector_process = ShapeDetectorProcess(exit_queue, shape_queue, websocket_queue, camera, detector, settings, detector_child_pipe)
    shape_processor_process = ShapeProcessorProcess(shape_queue, processed_shape_queue, websocket_queue, processor, processor_child_pipe)
    sticker_validator_process = StickerValidatorProcess(processed_shape_queue, results_queue, websocket_queue, validator, validator_child_pipe)
    validation_logger_process = ValidationResultsLogger(results_queue)

    context_manager.register_process("detector", detector_parent_pipe)
    context_manager.register_process("processor", processor_parent_pipe)
    context_manager.register_process("validator", validator_parent_pipe)

    processes = [shape_detector_process, shape_processor_process, sticker_validator_process, validation_logger_process]
    queues = [exit_queue, shape_queue, processed_shape_queue, results_queue, websocket_queue]


def restart_processes(background_tasks: BackgroundTasks):
    """Stop all processes and restart them with new settings while preserving queue content"""
    global settings, camera, detector, processor, validator, processes
    global shape_queue, processed_shape_queue, results_queue, websocket_queue, exit_queue
    global shape_detector_process, shape_processor_process, sticker_validator_process, validation_logger_process
    global detector_parent_pipe, detector_child_pipe, processor_parent_pipe, processor_child_pipe, validator_parent_pipe, validator_child_pipe
    start_time = time.time()
    logger.info("Starting complete system restart - saving queue content and terminating all processes")

    context_manager.save_contexts(
        shape_detector_process if 'shape_detector_process' in globals() else None,
        shape_processor_process if 'shape_processor_process' in globals() else None,
        sticker_validator_process if 'sticker_validator_process' in globals() else None,
    )

    saved_queue_content = {
        'shape_queue': [],
        'processed_shape_queue': [],
        'results_queue': [],
        'websocket_queue': []
    }

    for name, q in [
        ('shape_queue', shape_queue),
        ('processed_shape_queue', processed_shape_queue),
        ('results_queue', results_queue),
        ('websocket_queue', websocket_queue)
    ]:
        while not q.empty():
            try:
                saved_queue_content[name].append(q.get_nowait())
            except:
                pass
        logger.info(f"Saved {len(saved_queue_content[name])} items from {name}")

    exit_queue.put(None)

    for process in processes:
        if process.is_alive():
            logger.info(f"Terminating process: {process.name} (pid: {process.pid})")
            process.terminate()
            process.join(timeout=2)
            logger.info(f"Process {process.name} terminated")
        else:
            logger.info(f"Process {process.name} was not running")

    settings = get_settings()
    logger.info("Settings reloaded, recreating all components")

    if settings.camera_type == "video":
        camera = VideoFileCamera(settings.camera.video_path)
        logger.info(f"Created VideoFileCamera: {settings.camera.video_path}")
    else:
        camera = IPCamera(settings.camera.phone_ip, settings.camera.port)
        logger.info(f"Created IPCamera: {settings.camera.phone_ip}:{settings.camera.port}")

    detector = ShapeDetector(settings)
    processor = ShapeProcessor(settings)
    validator = StickerValidator()
    logger.info("Created new components")

    exit_queue = Queue()
    shape_queue = Queue()
    processed_shape_queue = Queue()
    results_queue = Queue()
    websocket_queue = Queue()

    shape_detector_process = ShapeDetectorProcess(exit_queue, shape_queue, websocket_queue, camera, detector, settings, detector_child_pipe)
    shape_processor_process = ShapeProcessorProcess(shape_queue, processed_shape_queue, websocket_queue, processor, processor_child_pipe)
    sticker_validator_process = StickerValidatorProcess(processed_shape_queue, results_queue, websocket_queue, validator, validator_child_pipe)
    validation_logger_process = ValidationResultsLogger(results_queue)

    context_manager.register_process("detector", detector_parent_pipe)
    context_manager.register_process("processor", processor_parent_pipe)
    context_manager.register_process("validator", validator_parent_pipe)

    logger.info("Created new process instances")

    processes = [shape_detector_process, shape_processor_process, sticker_validator_process, validation_logger_process]

    context_manager.restore_contexts(shape_detector_process, shape_processor_process, sticker_validator_process)

    logger.info("Restored process contexts")
    
    for name, q in [
        ('shape_queue', shape_queue),
        ('processed_shape_queue', processed_shape_queue),
        ('results_queue', results_queue),
        ('websocket_queue', websocket_queue)
    ]:
        for item in saved_queue_content[name]:
            q.put(item)
        logger.info(f"Restored {len(saved_queue_content[name])} items to {name}")

    for process in processes:
        logger.info(f"Starting process: {process.name}")
        process.start()
        logger.info(f"Process {process.name} started with pid: {process.pid}")

    logger.info("System restart completed")
    elapsed_time = time.time() - start_time
    logger.info(f"System restart completed in {elapsed_time:.2f} seconds")

    return {"status": "success", "message": "All processes restarted with updated settings and preserved queue data"}

init_processes()


async def stream_images_async():
    logger.info(f"stream_images starting")
    last_time = datetime.datetime.now()

    from utils.env import OS_TYPE

    while True:
        try:
            msg: StreamingMessage = websocket_queue.get_nowait()

            if msg is None:
                raise InterruptedError

            await manager.broadcast_message(msg)

        except queue.Empty:
            pass
        except (KeyboardInterrupt, InterruptedError):
            logger.info(f"stream_images exiting")
            return
        except Exception as e:
            logger.error(f"stream_images exception: ", str(e), type(e))

        current_time = datetime.datetime.now()
        if current_time - last_time > datetime.timedelta(seconds=5):
            last_time = current_time
            #logger.info(f'shape: {shape_queue.qsize()}, processed_shape: {processed_shape_queue.qsize()}, results: {results_queue.qsize()}, ws: {websocket_queue.qsize()}')

        if OS_TYPE == "MACOS":
            await asyncio.sleep(0.016)


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

    for process in processes:
        if process.is_alive():
            process.terminate()


@app.websocket("/ws")
async def websocket_connect(websocket: WebSocket):
    try:
        await manager.connect(websocket)
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect as e:
        manager.disconnect(websocket)
        if e.code != 1000:
            logger.warn(f'websocket closed: code {e.code}')


@app.post("/stream/start")
async def start_stream_endpoint(background_tasks: BackgroundTasks):
    start_processes(background_tasks)
    return {"status": "streaming started"}


@app.post("/stream/stop")
async def stop_stream():
    stop_processes()
    return {"status": "streaming stopped"}

@app.post("/stream/restart")
async def restart_stream(background_tasks: BackgroundTasks):
    return restart_processes(background_tasks)


@app.get("/sticker/parameters")
async def get_sticker_parameters():
    global sticker_validator_process
    params = sticker_validator_process.get_validator_parameters()
    return params.to_dict()


@app.post("/sticker/parameters")
async def set_sticker_parameters(params_dict: dict):
    global sticker_validator_process, validator
    sticker_params = StickerValidationParams.from_dict(params_dict)
    sticker_validator_process.set_validator_parameters(sticker_params)
    save_sticker_parameters(sticker_params)
    return {"status": "success", "message": "Sticker parameters updated"}


@app.get("/validation/logs")
def get_validation_logs(
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None,
        page: int = Query(1, ge=1),
        page_size: int = Query(100, ge=1, le=1000),
):
    """Get validation logs with date filtering and pagination"""
    return paginate_validation_logs(start_date, end_date, page, page_size)


@app.delete("/validation/logs/{log_id}")
def delete_validation_log(log_id: int):
    """Delete a specific validation log by ID"""
    return delete_validation_log_by_id(log_id)


@app.delete("/validation/logs")
def delete_all_validation_logs_endpoint():
    """Delete all validation logs from the database"""
    return delete_all_validation_logs()

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/")
def get_app_settings():
    """Get current application settings"""
    settings = get_settings()
    return settings.to_dict()

@app.get("/validation/stats")
def get_validation_statistics(
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None
):
    """Get validation statistics for a given time period"""
    from backend.db import get_validation_stats
    return get_validation_stats(start_date, end_date)

@router.post("/apply")
def apply_settings(settings_data: dict, background_tasks: BackgroundTasks):
    """Update settings and restart processes to apply them"""
    try:
        logger.info(f"new settings: {settings_data}")
        new_settings = Settings.from_dict(settings_data)
        logger.info(f"settings updated: {new_settings}")
        save_settings(new_settings)
        system_running = any(process.is_alive() for process in processes)

        if system_running:
            result = restart_processes(background_tasks)
            logger.info(f"Settings applied and processes restarted")
            return {"success": True, "message": "Settings applied and processes restarted"}
        else:
            logger.info(f"Settings applied (system not running, no restart needed)")
            return {"success": True, "message": "Settings applied (system not running, no restart needed)"}
    except Exception as e:
        logger.error(f"Failed to apply settings: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Failed to apply settings: {str(e)}"}


from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, Body


@app.post("/set-empty-conveyor")
def set_empty_conveyor_background(
        background_tasks: BackgroundTasks,
        image_data: dict = Body(...)
):
    """Set uploaded image as empty conveyor background"""
    try:
        image_base64 = image_data.get("image")

        if not image_base64:
            return {"success": False, "message": "No image data provided"}

        result = save_and_set_empty_conveyor_background(image_base64)

        if result["success"]:
            restart_processes(background_tasks)

        return result
    except Exception as e:
        logger.error(f"Failed to set empty conveyor background: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}


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
        .logs-section { margin-top: 30px; }
        .logs-controls { margin-bottom: 15px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
        #logsTable { width: 100%; border-collapse: collapse; }
        #logsTable th, #logsTable td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        #logsTable th { background-color: #f2f2f2; }
        .pagination { margin-top: 15px; }
        .pagination button { margin-right: 5px; }
        /* New Latest Validation Styles */
        #latestValidation { 
            margin-top: 20px; 
            border: 2px solid #007bff; 
            border-radius: 5px; 
            padding: 15px; 
            background-color: #f8f9fa; 
        }
        .validation-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .validation-status {
            padding: 5px 10px;
            border-radius: 4px;
            font-weight: bold;
        }
        .status-success { background-color: #d4edda; color: #155724; }
        .status-warning { background-color: #fff3cd; color: #856404; }
        .status-danger { background-color: #f8d7da; color: #721c24; }
        .validation-details { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .validation-image { text-align: center; }
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
 <div id="latestValidation">
        <div class="validation-header">
            <h2>Latest Validation</h2>
            <div id="validationStatus" class="validation-status">No data</div>
        </div>
        <div class="validation-details">
            <div>
                <h3>Results</h3>
                <table id="validationTable">
                    <tr><th>Property</th><th>Value</th></tr>
                    <tr><td>Sequence Number</td><td id="seqNumber">-</td></tr>
                    <tr><td>Detection Time</td><td id="detectionTime">-</td></tr>
                    <tr><td>Sticker Present</td><td id="stickerPresent">-</td></tr>
                    <tr><td>Sticker Matches Design</td><td id="stickerMatches">-</td></tr>
                    <tr><td>Sticker Center Position (X, Y)</td><td id="stickerPosition">-</td></tr>
                    <tr><td>Sticker Size (W, H)</td><td id="stickerSize">-</td></tr>
                    <tr><td>Rotation</td><td id="stickerRotation">-</td></tr>
                </table>
            </div>
            <div class="validation-image">
                <img id="validationImage" src="" alt="Validation result" style="max-height: 200px; display: none;">
            </div>
        </div>
    </div>
    </div>
    <h2>Detection Events</h2>
    <div id="events"></div>

    <div class="logs-section">
        <h2>Validation Logs</h2>
        <div class="logs-controls">
            <label>
                Start Date:
                <input type="datetime-local" id="startDate">
            </label>
            <label>
                End Date:
                <input type="datetime-local" id="endDate">
            </label>
            <label>
                Page:
                <input type="number" id="page" value="1" min="1" style="width: 60px;">
            </label>
            <label>
                Items per page:
                <select id="pageSize">
                    <option value="10">10</option>
                    <option value="50">50</option>
                    <option value="100" selected>100</option>
                    <option value="500">500</option>
                    <option value="1000">1000</option>
                </select>
            </label>
            <button id="fetchLogsBtn">Fetch Logs</button>
        </div>
        <table id="logsTable">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Timestamp</th>
                    <th>Seq #</th>
                    <th>Sticker Present</th>
                    <th>Matches Design</th>
                    <th>Position</th>
                    <th>Size</th>
                    <th>Rotation</th>
                </tr>
            </thead>
            <tbody id="logsTableBody"></tbody>
        </table>
        <div class="pagination">
            <span id="paginationInfo">No logs fetched yet</span>
            <button id="prevPageBtn" disabled>Previous</button>
            <button id="nextPageBtn" disabled>Next</button>
        </div>
    </div>
    <div class="parameter-section">
    <h2>Sticker Parameters</h2>
    <div id="parameterForm" class="parameter-form">
        <div class="param-group">
            <h3>Sticker Center</h3>
            <div class="form-row">
                <label>X: <input type="number" id="centerX" step="1" min="0"></label>
                <label>Y: <input type="number" id="centerY" step="1" min="0"></label>
            </div>
        </div>

        <div class="param-group">
            <h3>Acc Size</h3>
            <div class="form-row">
                <label>Width: <input type="number" id="accWidth" step="1"></label>
                <label>Height: <input type="number" id="accHeight" step="1"></label>
            </div>
        </div>

        <div class="param-group">
            <h3>Sticker Size</h3>
            <div class="form-row">
                <label>Width: <input type="number" id="stickerWidth" step="0.1"></label>
                <label>Height: <input type="number" id="stickerHeight" step="0.1"></label>
            </div>
        </div>

        <div class="param-group">
            <h3>Sticker Rotation</h3>
            <div class="form-row">
                <label>Angle (degrees): <input type="number" id="stickerRotation" step="0.1"></label>
            </div>
        </div>

        <div class="param-group">
            <h3>Sticker Design</h3>
            <div class="design-preview">
                <img id="stickerDesign" src="" alt="No sticker design available">
            </div>
            <input type="file" id="stickerDesignUpload" accept="image/*">
        </div>

        <div class="action-buttons">
            <button id="loadParamsBtn">Load Current Parameters</button>
            <button id="saveParamsBtn">Save Parameters</button>
        </div>
    </div>
    <div class="app-settings-section">
  <h2>Application Settings</h2>
  <div class="parameter-form">
    <div class="param-group">
      <h3>Camera</h3>
      <label>Camera Type:
        <select id="cameraType">
          <option value="video">Video File</option>
          <option value="ip">IP Camera</option>
        </select>
      </label>
      <label>IP Camera Address: <input type="text" id="cameraIp"></label>
      <label>IP Camera Port: <input type="number" id="cameraPort"></label>
      <label>Video File Path: <input type="text" id="videoPath"></label>
    </div>
    <div class="param-group">
      <h3>Detection</h3>
      <label>Border Left: <input type="number" id="detBorderLeft" step="0.01" min="0" max="1"></label>
      <label>Border Right: <input type="number" id="detBorderRight" step="0.01" min="0" max="1"></label>
      <label>Line Height: <input type="number" id="detLineHeight" step="0.01" min="0" max="1"></label>
    </div>
    <div class="param-group">
      <h3>Processing</h3>
      <label>Downscale Width: <input type="number" id="procWidth" step="1" min="1"></label>
      <label>Downscale Height: <input type="number" id="procHeight" step="1" min="1"></label>
      <label>Background Photo Path: <input type="text" id="bgPhotoPath"></label>
    </div>
    <div class="param-group">
      <h3>Validation</h3>
      <label>Position Tolerance %: <input type="number" id="valPosTol" step="0.1" min="0"></label>
      <label>Rotation Tolerance °: <input type="number" id="valRotTol" step="0.1" min="0"></label>
      <label>Size Ratio Tol: <input type="number" id="valSizeTol" step="0.001" min="0"></label>
    </div>
    <div class="param-group">
      <h3>File Paths</h3>
      <label>Database URL: <input type="text" id="dbUrl"></label>
      <label>Sticker Params File: <input type="text" id="stickerParamsFile"></label>
      <label>Sticker Design Path: <input type="text" id="stickerDesignPath"></label>
      <label>Sticker Output Path: <input type="text" id="stickerOutputPath"></label>
    </div>
    <div class="action-buttons">
      <button id="loadAppSettingsBtn">Load App Settings</button>
      <button id="saveAppSettingsBtn">Save App Settings</button>
      <button id="restartSystemBtn">Save & Restart System</button>
    </div>
  </div>
</div>
</div>
<style>
    /* Parameter form styling */
    .parameter-form {
        border: 1px solid #ddd;
        padding: 15px;
        margin-bottom: 20px;
        background-color: #f9f9f9;
    }
    .param-group {
        margin-bottom: 15px;
    }
    .form-row {
        display: flex;
        gap: 15px;
        margin-bottom: 10px;
    }
    .form-row label {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }
    .design-preview {
        margin: 10px 0;
        border: 1px dashed #ccc;
        padding: 5px;
        text-align: center;
    }
    .design-preview img {
        max-height: 150px;
        max-width: 100%;
    }
    .action-buttons {
        margin-top: 15px;
    }
</style>

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

            ws.onmessage = function(event) {
            const data = JSON.parse(event.data);

            // Process different message types
            if (data.type === 1) { // RAW
                document.getElementById('rawStream').src = 'data:image/jpeg;base64,' + JSON.parse(data.content).image;
            } else if (data.type === 2) { // SHAPE
                document.getElementById('shapeStream').src = 'data:image/jpeg;base64,' + JSON.parse(data.content).image;
            } else if (data.type === 3) { // PROCESSED
                document.getElementById('processedStream').src = 'data:image/jpeg;base64,' + JSON.parse(data.content).image;
            } else if (data.type === 4) { // VALIDATION
                const validationData = JSON.parse(data.content).ValidationResult;
                updateLatestValidation(validationData);
                addEvent(`Validation received: Seq#${validationData.SeqNumber}, Present: ${validationData.StickerPresent}, Matches: ${validationData.StickerMatchesDesign}`);
            }
        };
        }

        function updateLatestValidation(result) {
            // Update status indicator
            const statusElement = document.getElementById('validationStatus');
            statusElement.textContent = getStatusText(result);
            statusElement.className = 'validation-status ' + getStatusClass(result);

            // Update table values
            document.getElementById('seqNumber').textContent = result.SeqNumber;
            document.getElementById('detectionTime').textContent = new Date(result.Timestamp).toLocaleString();
            document.getElementById('stickerPresent').textContent = result.StickerPresent;
            document.getElementById('stickerMatches').textContent = result.StickerMatchesDesign !== null ? result.StickerMatchesDesign : 'N/A';

            // Update position, size, rotation
            if (result.StickerPosition) {
                document.getElementById('stickerPosition').textContent = 
                    `X: ${result.StickerPosition.X.toFixed(1)}, Y: ${result.StickerPosition.Y.toFixed(1)}`;
            } else {
                document.getElementById('stickerPosition').textContent = 'N/A';
            }

            if (result.StickerSize) {
                document.getElementById('stickerSize').textContent = 
                    `W: ${result.StickerSize.Width.toFixed(1)}, H: ${result.StickerSize.Height.toFixed(1)}`;
            } else {
                document.getElementById('stickerSize').textContent = 'N/A';
            }

            document.getElementById('stickerRotation').textContent = 
                result.StickerRotation !== null ? `${result.StickerRotation.toFixed(1)}°` : 'N/A';

            // Update image
            const imgElement = document.getElementById('validationImage');
            if (result.Image) {
                imgElement.src = 'data:image/png;base64,' + result.Image;
                imgElement.style.display = 'block';
            } else {
                imgElement.style.display = 'none';
            }
        }

        function getStatusText(result) {
            if (!result.StickerPresent) {
                return 'NO STICKER';
            } else if (result.StickerMatchesDesign === false) {
                return 'INVALID PLACEMENT';
            } else if (result.StickerMatchesDesign === true) {
                return 'VALID';
            } else {
                return 'UNKNOWN';
            }
        }

        function getStatusClass(result) {
            if (!result.StickerPresent) {
                return 'status-warning';
            } else if (result.StickerMatchesDesign === false) {
                return 'status-danger';
            } else if (result.StickerMatchesDesign === true) {
                return 'status-success';
            } else {
                return '';
            }
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

        // Logs handling
        let currentPage = 1;
        let totalPages = 0;
        let totalLogs = 0;

        document.getElementById('fetchLogsBtn').addEventListener('click', fetchLogs);
        document.getElementById('prevPageBtn').addEventListener('click', () => {
            if (currentPage > 1) {
                document.getElementById('page').value = --currentPage;
                fetchLogs();
            }
        });
        document.getElementById('nextPageBtn').addEventListener('click', () => {
            if (currentPage < totalPages) {
                document.getElementById('page').value = ++currentPage;
                fetchLogs();
            }
        });

        async function fetchLogs() {
            try {
                const startDate = document.getElementById('startDate').value;
                const endDate = document.getElementById('endDate').value;
                const page = document.getElementById('page').value || 1;
                const pageSize = document.getElementById('pageSize').value;

                currentPage = parseInt(page);

                let url = `/validation/logs?page=${page}&page_size=${pageSize}`;
                if (startDate) url += `&start_date=${encodeURIComponent(startDate)}`;
                if (endDate) url += `&end_date=${encodeURIComponent(endDate)}`;

                const response = await fetch(url);
                const data = await response.json();

                // Update pagination info
                totalPages = data.pages;
                totalLogs = data.total;
                document.getElementById('paginationInfo').textContent = 
                    `Page ${data.page} of ${data.pages} (${data.total} logs total)`;

                // Enable/disable pagination buttons
                document.getElementById('prevPageBtn').disabled = data.page <= 1;
                document.getElementById('nextPageBtn').disabled = data.page >= data.pages;

                // Display logs
                const tbody = document.getElementById('logsTableBody');
                tbody.innerHTML = '';

                data.Logs.forEach(log => {
                const row = document.createElement('tr');

                // Format position and size if available
                const Position = log.StickerPosition 
                    ? `X: ${log.StickerPosition.x.toFixed(1)}, Y: ${log.StickerPosition.y.toFixed(1)}` 
                    : 'N/A';

                const Size = log.StickerSize 
                    ? `W: ${log.StickerSize.width.toFixed(1)}, H: ${log.StickerSize.height.toFixed(1)}` 
                    : 'N/A';

                // Format Timestamp
                const Timestamp = new Date(log.Timestamp).toLocaleString();  // Fixed variable declaration

                row.innerHTML = `
                    <td>${log.Id}</td>
                    <td>${Timestamp}</td>
                    <td>${log.SeqNumber}</td>
                    <td>${log.StickerPresent ? '✓' : '✗'}</td>
                    <td>${log.StickerMatchesDesign === null ? 'N/A' : log.StickerMatchesDesign ? '✓' : '✗'}</td>
                    <td>${Position}</td>
                    <td>${Size}</td>
                    <td>${log.StickerRotation !== null ? log.StickerRotation.toFixed(1) + '°' : 'N/A'}</td>
                `;

                tbody.appendChild(row);
            });
                addEvent(`Fetched ${data.logs.length} logs (page ${data.page}/${data.pages})`);
            } catch (e) {
                console.error('Error fetching logs:', e);
                addEvent(`Error fetching logs: ${e.message}`);
            }
        }
        document.getElementById('loadParamsBtn').addEventListener('click', loadParameters);
    document.getElementById('saveParamsBtn').addEventListener('click', saveParameters);
    document.getElementById('stickerDesignUpload').addEventListener('change', handleDesignUpload);
    async function loadAppSettings() {
            try {
                const res = await fetch('/settings/');
                const cfg = await res.json();

                // Camera settings - updated for PascalCase format
                document.getElementById('cameraType').value = cfg.CameraType || 'video';
                document.getElementById('cameraIp').value = cfg.Camera.PhoneIp;
                document.getElementById('cameraPort').value = cfg.Camera.Port;
                document.getElementById('videoPath').value = cfg.Camera.VideoPath;

                // Detection settings - updated for PascalCase format
                document.getElementById('detBorderLeft').value = cfg.Detection.DetectionBorderLeft;
                document.getElementById('detBorderRight').value = cfg.Detection.DetectionBorderRight;
                document.getElementById('detLineHeight').value = cfg.Detection.DetectionLineHeight;

                // Processing settings - updated for PascalCase format
                document.getElementById('procWidth').value = cfg.Processing.DownscaleWidth;
                document.getElementById('procHeight').value = cfg.Processing.DownscaleHeight;
                document.getElementById('bgPhotoPath').value = cfg.BgPhotoPath || '';

                // Validation settings - updated for PascalCase format
                document.getElementById('valPosTol').value = cfg.Validation.PositionTolerancePercent;
                document.getElementById('valRotTol').value = cfg.Validation.RotationToleranceDegrees;
                document.getElementById('valSizeTol').value = cfg.Validation.SizeRatioTolerance;

                // File paths - updated for PascalCase format
                document.getElementById('dbUrl').value = cfg.DatabaseUrl;
                document.getElementById('stickerParamsFile').value = cfg.StickerParamsFile;
                document.getElementById('stickerDesignPath').value = cfg.StickerDesignPath;
                document.getElementById('stickerOutputPath').value = cfg.StickerOutputPath;

                addEvent('App settings loaded');
            } catch (e) {
                console.error(e);
                addEvent('Error loading app settings: ' + e.message);
            }
        }

  async function saveAppSettings() {
            try {
                const payload = {
                    // Using PascalCase for compatibility with from_dict
                    CameraType: document.getElementById('cameraType').value,
                    BgPhotoPath: document.getElementById('bgPhotoPath').value,
                    DatabaseUrl: document.getElementById('dbUrl').value,
                    StickerParamsFile: document.getElementById('stickerParamsFile').value,
                    StickerDesignPath: document.getElementById('stickerDesignPath').value,
                    StickerOutputPath: document.getElementById('stickerOutputPath').value,
                    Detection: {
                        DetectionBorderLeft: parseFloat(document.getElementById('detBorderLeft').value),
                        DetectionBorderRight: parseFloat(document.getElementById('detBorderRight').value),
                        DetectionLineHeight: parseFloat(document.getElementById('detLineHeight').value)
                    },
                    Processing: {
                        DownscaleWidth: parseInt(document.getElementById('procWidth').value),
                        DownscaleHeight: parseInt(document.getElementById('procHeight').value)
                    },
                    Validation: {
                        PositionTolerancePercent: parseFloat(document.getElementById('valPosTol').value),
                        RotationToleranceDegrees: parseFloat(document.getElementById('valRotTol').value),
                        SizeRatioTolerance: parseFloat(document.getElementById('valSizeTol').value)
                    },
                    Camera: {
                        PhoneIp: document.getElementById('cameraIp').value,
                        Port: parseInt(document.getElementById('cameraPort').value),
                        VideoPath: document.getElementById('videoPath').value
                    }
                };

                const res = await fetch('/settings/apply', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const result = await res.json();
                addEvent('App settings saved: ' + JSON.stringify(result));
                return result;
            } catch (e) {
                console.error(e);
                addEvent('Error saving app settings: ' + e.message);
                return { success: false, message: e.message };
            }
        }


  document.getElementById('loadAppSettingsBtn').addEventListener('click', loadAppSettings);
  document.getElementById('saveAppSettingsBtn').addEventListener('click', saveAppSettings);
  document.getElementById('restartSystemBtn').addEventListener('click', async () => {
    const saveResult = await saveAppSettings();
    if (saveResult.success) {
      try {
        const res = await fetch('/stream/restart', { method: 'POST' });
        const result = await res.json();
        addEvent('System restarted: ' + JSON.stringify(result));
      } catch (e) {
        addEvent('Error restarting system: ' + e.message);
      }
    }
  });

  // Auto-load settings on page load
  document.addEventListener('DOMContentLoaded', loadAppSettings);
    let currentDesignImage = null;

    async function loadParameters() {
        try {
            const response = await fetch('/sticker/parameters');
            const params = await response.json();

            // Fill in form fields
            document.getElementById('centerX').value = params.StickerCenter.X;
            document.getElementById('centerY').value = params.StickerCenter.Y;
            document.getElementById('accWidth').value = params.AccSize.Width;
            document.getElementById('accHeight').value = params.AccSize.Height;
            document.getElementById('stickerWidth').value = params.StickerSize.Width;
            document.getElementById('stickerHeight').value = params.StickerSize.Height;
            document.getElementById('stickerRotation').value = params.StickerRotation;

            // Display sticker design
            if (params.StickerDesign) {
                document.getElementById('stickerDesign').src = 'data:image/png;base64,' + params.StickerDesign;
                currentDesignImage = params.StickerDesign;
            }

            addEvent('Parameters loaded successfully');
        } catch (e) {
            console.error('Error loading parameters:', e);
            addEvent(`Error loading parameters: ${e.message}`);
        }
    }

    function handleDesignUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            // Display the image
            document.getElementById('stickerDesign').src = e.target.result;
            // Extract the base64 data (remove the prefix)
            currentDesignImage = e.target.result.split(',')[1];
        };
        reader.readAsDataURL(file);
    }

    async function saveParameters() {
        try {
            const params = {
                StickerDesign: currentDesignImage,
                StickerCenter: {
                    X: parseFloat(document.getElementById('centerX').value),
                    Y: parseFloat(document.getElementById('centerY').value)
                },
                AccSize: {
                    Width: parseFloat(document.getElementById('accWidth').value),
                    Height: parseFloat(document.getElementById('accHeight').value)
                },
                StickerSize: {
                    Width: parseFloat(document.getElementById('stickerWidth').value),
                    Height: parseFloat(document.getElementById('stickerHeight').value)
                },
                StickerRotation: parseFloat(document.getElementById('stickerRotation').value)
            };

            const response = await fetch('/sticker/parameters', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(params)
            });

            const result = await response.json();
            addEvent(`Parameters saved: ${JSON.stringify(result)}`);
        } catch (e) {
            console.error('Error saving parameters:', e);
            addEvent(`Error saving parameters: ${e.message}`);
        }
    }

    // Load parameters on page load
    document.addEventListener('DOMContentLoaded', loadParameters);
    </script>
</body>
</html>
    """
