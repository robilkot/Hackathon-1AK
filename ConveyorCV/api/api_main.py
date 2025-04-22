import uvicorn
import os
from dotenv import load_dotenv
from api.api import app

load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("api_main:app", host="0.0.0.0", port=port, reload=True)