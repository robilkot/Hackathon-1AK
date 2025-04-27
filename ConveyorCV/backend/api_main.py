import multiprocessing

import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

from api import app

from fastapi.openapi.utils import get_openapi

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
    port = int(os.getenv("API_PORT", "8000"))
    print(f"API documentation available at http://localhost:{port}/docs")
    uvicorn.run("api_main:app", host="0.0.0.0", port=port, reload=True)