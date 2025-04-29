import asyncio
import datetime
import logging
import queue
from contextlib import asynccontextmanager
from multiprocessing import Queue, Process
from sqlalchemy.orm import Session
from fastapi import Depends, Query
from typing import Optional

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse

from Camera.CameraInterface import CameraInterface
from Camera.IPCamera import IPCamera
from Camera.VideoFileCamera import VideoFileCamera
from algorithms.ShapeDetector import ShapeDetector
from algorithms.ShapeProcessor import ShapeProcessor
from algorithms.StickerValidator import StickerValidator
from backend.db import paginate_validation_logs, delete_validation_log_by_id
from model.model import StickerValidationParams, StreamingMessage
from processes import ShapeDetectorProcess, ShapeProcessorProcess, StickerValidatorProcess, ValidationResultsLogger
from settings import get_settings
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

logger = logging.getLogger(__name__)

settings = get_settings()

manager = WebSocketManager()

camera: CameraInterface
if settings.camera_type == "video":
    camera = VideoFileCamera(settings.camera.video_path)
else:
    camera = IPCamera(settings.camera.phone_ip, settings.camera.port)

# todo delete if this is bullshit
sticker_design = cv2.imread(settings.sticker_design_path)
if sticker_design is None:
    raise Exception("sticker_design not found")

# todo make it correct
sticker_validator_params = StickerValidationParams(
    sticker_design=sticker_design,
    sticker_center=(50.0, 50.0),  # Default center point
    acc_size=(200.0, 200.0),  # Default acceptable size
    sticker_size=(100.0, 100.0),  # Default sticker size
    sticker_rotation=0.0  # Default rotation angle
)

detector = ShapeDetector()
processor = ShapeProcessor()
validator = StickerValidator(sticker_validator_params)

exit_queue: Queue
shape_queue: Queue
processed_shape_queue: Queue
results_queue: Queue
websocket_queue: Queue
shape_detector_process: ShapeDetectorProcess
shape_processor_process: ShapeProcessorProcess
sticker_validator_process: StickerValidatorProcess
validation_logger_process: ValidationResultsLogger
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
    sticker_validator_process = StickerValidatorProcess(processed_shape_queue, results_queue, websocket_queue,
                                                        validator)
    validation_logger_process = ValidationResultsLogger(results_queue)

    processes = [shape_detector_process, shape_processor_process, sticker_validator_process, validation_logger_process]
    queues = [exit_queue, shape_queue, processed_shape_queue, results_queue, websocket_queue]


init_processes()


async def stream_images_async():
    logger.info(f"stream_images starting")
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
            logger.info(f"stream_images exiting")
            return
        except Exception as e:
            logger.error(f"stream_images exception: ", str(e), type(e))

        current_time = datetime.datetime.now()
        if current_time - last_time > datetime.timedelta(seconds=2):
            last_time = current_time
            # print('shape_queue: ', shape_queue.qsize())
            # print('processed_shape_queue: ', processed_shape_queue.qsize())
            # print('results_queue: ', results_queue.qsize())
            # print('websocket_queue: ', websocket_queue.qsize())

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


@app.get("/sticker/parameters")
async def get_sticker_parameters():
    params = validator.get_parameters()
    return params.to_dict()


@app.post("/sticker/parameters")
async def set_sticker_parameters(params_dict: dict):
    global sticker_validator_process
    global validator

    sticker_params = StickerValidationParams.from_dict(params_dict)
    logger.info(f'updated validation params: {str(sticker_params)}')

    sticker_validator_process.set_validator_parameters(sticker_params)

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
def delete_all_validation_logs():
    """Delete all validation logs from the database"""
    return delete_all_validation_logs()

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
                            handleValidationResult(contentObj.ValidationResult);
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

            const stickerPresent = result.StickerPresent;
            const stickerMatchesDesign = result.StickerMatchesDesign;
            const seqNumber = result.SeqNumber;

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
    </script>
</body>
</html>
    """
