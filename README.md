# Sticker quality control system from command ```__main__```

### A computer vision system for automated quality control of sticker placement. The application detects objects on a conveyor belt, validates whether stickers are properly applied (presence, position, orientation, and size), and logs validation results for quality assurance reporting.

## Implementation Details:

### Features

- Real-time sticker validation on conveyor belt
- Parameter configuration
- Validation history logs and statistics
- Support for IP cameras and video files as input
- Interactive UI with notifications for user feedback
- Dynamic system reconfiguration without restart

### Architecture

![Screenshot 2025-05-06 at 6 38 29 pm](https://github.com/user-attachments/assets/78c7cd4c-8d92-4b1e-b329-47a12744bcd7)

#### Input Layer: IP Camera or Video file

  The system starts with an IP camera, which captures real-time video or images as the raw input for further processing.
  
#### Processing Layer

  The system uses multiple processes for different stages of image processing: detection, processing, and validation
  Inter-process communication happens through queues and named pipes.
  - ShapeDetector process captures frames and use background subtraction to detect objects on the conveyor
  - ShapeProcessor process processes extracts and transforms the regions of interest
  - StickerValidator process extracted regions to validate sticker presence and positioning
  - 
#### Backend Layer: FastAPI

  FastAPI acts as the central communication hub. Handles API requests/responses. Coordinates interaction between the core detection/processing system and external clients.
  
#### Client Layer

  This layer provides user interfaces for different platforms: 
  - Avalonia Desktop Desktop GUI built with Avalonia for native performance and rich UI.  
  - Avalonia WASM WebAssembly version of the Avalonia app, allowing the same interface to run in browsers.
  - Web Likely a general web interface or dashboard that interacts with the FastAPI backend.

## Setup


## Requirements:

  1. Python: version 3.13 or higher
  2. C#: any modern version (preferably with .NET 7 or later)
  3. Avalonia UI: cross-platform UI framework (latest stable version recommended)

## Topics Related & Technologies Used

  OpenCV, FastAPI, Multiprocessing, SQLAlchemy, IP-camera, WebSocket, SQLite, IPC, TemplateMatching, Morphology, AvaloniaUI, C#.

## Made By 

- [@NikitaKalabin](https://github.com/NikitaKalabin)
- [@robilkot](https://github.com/robilkot)
- [@maxkrivenya](https://github.com/maxkrivenya)
