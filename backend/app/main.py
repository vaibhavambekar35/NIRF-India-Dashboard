import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api.endpoints import router as api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Production-grade API for NIRF Insight: India State-wise Ranking Distribution Dashboard"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith((".js", ".css", ".html", ".json")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Support all route prefix patterns: /api/v1 (primary), /v1, and legacy /api
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/v1")
app.include_router(api_router, prefix="/api")

@app.get("/api/health")
@app.get("/health")
def health():
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.PROJECT_VERSION}

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Serve GeoJSON
GEOJSON_PATHS = [
    os.path.join(BASE_DIR, "public", "geojson", "india_states.geojson"),
    os.path.join(BASE_DIR, "india_states.geojson"),
    "/var/task/india_states.geojson",
    "/var/task/public/geojson/india_states.geojson"
]

@app.get("/public/geojson/india_states.geojson")
@app.get("/india_states.geojson")
def get_india_geojson():
    for p in GEOJSON_PATHS:
        if os.path.exists(p):
            return FileResponse(p, media_type="application/json")
    return HTMLResponse("GeoJSON file not found", status_code=404)

# Mount frontend static directory
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

@app.get("/style.css")
def get_style():
    style_p = os.path.join(BASE_DIR, "style.css")
    if os.path.exists(style_p):
        return FileResponse(style_p, media_type="text/css")
    return HTMLResponse("style.css not found", status_code=404)

@app.get("/app.js")
def get_app_js():
    js_p = os.path.join(BASE_DIR, "app.js")
    if os.path.exists(js_p):
        return FileResponse(js_p, media_type="application/javascript")
    return HTMLResponse("app.js not found", status_code=404)

@app.get("/View PDF")
@app.get("/View%20PDF")
def redirect_view_pdf():
    return RedirectResponse(url="/", status_code=302)

@app.get("/")
def serve_dashboard():
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return HTMLResponse("<h1>NIRF Insight Dashboard index.html not found</h1>", status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
