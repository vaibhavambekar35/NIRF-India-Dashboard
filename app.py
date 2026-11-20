import os
import sys

# Ensure root directory is in sys.path so 'backend' package resolves properly
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Expose production FastAPI app for Vercel and ASGI runners
from backend.app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
