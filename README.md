# Sticker quality control system
A computer vision system for automated quality control of sticker placement. The application detects objects on a conveyor belt, validates whether stickers are properly applied (presence, position, orientation, and size), and logs validation results for quality assurance reporting.

## Features
- Real-time sticker validation on conveyor belt
- Design configuration with user-friendly UI
- Validation logs and statistics
- Support for IP cameras and video files as input
- Interactive UI with notifications for user feedback
- Dynamic algorithms configuration without system restart

## Screenshots
Main window
![image](https://github.com/user-attachments/assets/3a35ef14-1688-4dd3-bd08-ffbb62718cfe)

Detection of wrong design (rotation of sticker does not match design)
![image](https://github.com/user-attachments/assets/2a975371-ebb3-46d8-9863-2b8614d5211b)

Detection of wrong design (location of sticker does not match design)
![image](https://github.com/user-attachments/assets/9ed11d42-0341-4342-952a-9903fd61ca9d)

Configuration of design
![image](https://github.com/user-attachments/assets/ba77f524-e924-4555-8c48-cfe43ad12656)

Validation log and statistics window
![image](https://github.com/user-attachments/assets/cb2444ad-0527-45ac-9432-5b475ed7385f)

Manual review of wrong design detection
![image](https://github.com/user-attachments/assets/15729474-745b-4696-9ebc-31b8ffdc4862)


## Implementation details:

### Architecture
![Screenshot 2025-05-06 at 6 38 29 pm](https://github.com/user-attachments/assets/78c7cd4c-8d92-4b1e-b329-47a12744bcd7)

#### Input: IP camera or video file
The system starts with an IP camera, which captures real-time video or frames from video file as the input for further processing.

#### Backend
FastAPI acts as the central communication hub. Handles API requests/responses. Coordinates interaction between the core detection/processing system and external clients.
  
The system uses multiple processes for different CPU-bound stages of image processing: moving shape detection, shape processing, and sticker validation.
- ShapeDetector captures frames and uses background subtraction to detect moving objects on the conveyor belt
- ShapeProcessor extracts and transforms the regions of interest (detects batteries on conveyor belt, tracks sequence numbers of those)
- StickerValidator analyzes processed images to check for sticker presense and validates design and positioning according with provided parameters
Processes communicate validation data using queues. Configuration messages are sent using pipes.
  
#### Frontend
Provides graphical interfaces for different platforms: 
- Avalonia Desktop GUI for cross-platform native performance and rich UI.  
- Avalonia WebAssembly version allows the same interface to run in browsers.
- HTML/CSS/JS web interface (dashboard) that interacts with the FastAPI backend.

## Technologies Used
Python, OpenCV, TemplateMatching, Multiprocessing, FastAPI, WebSocket, SQLAlchemy, SQLite, C#, AvaloniaUI.

## Setup


## Requirements:
Python 3.13 or higher

.NET 8.0 or higher

Avalonia 11.3.0 or higher

## built by ```__main__```
- [@NikitaKalabin](https://github.com/NikitaKalabin)
- [@robilkot](https://github.com/robilkot)
- [@maxkrivenya](https://github.com/maxkrivenya)
