import multiprocessing

import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

import logging
import logging.config
from api import app, router

from fastapi.openapi.utils import get_openapi

# Configure logging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(levelname)s %(asctime)s %(name)s - %(message)s",
            "datefmt": "%H:%M:%S"  # Only shows hours:minutes:seconds
        }
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {
            "level": os.environ.get("LOG_LEVEL", "INFO"),
            "handlers": ["default"],
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="ConveyorCV API",
        version="1.0.0",
        description="API for conveyor belt detection and sticker validation",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    multiprocessing.set_start_method('spawn', force=True)
    app.include_router(router)
    port = int(os.getenv("API_PORT", "8000"))
    logger.info(f"API documentation available at http://localhost:{port}/docs")
    logger.info(f"Example available at http://localhost:{port}/example")
    uvicorn.run("api_main:app", host="127.0.0.1", port=port, reload=False)