import os
import sys
import uuid
import threading
import logging
from typing import Dict, Any, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pydantic import BaseModel
import yt_dlp

from translator import TARGET_LANGUAGES
from pipeline import DubbingPipeline

# Ensure FFmpeg is accessible
WINGET_LINKS = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Links"
if os.path.exists(WINGET_LINKS) and WINGET_LINKS not in os.environ.get("PATH", ""):
    os.environ["PATH"] = WINGET_LINKS + os.pathsep + os.environ.get("PATH", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebServer")

app = FastAPI(title="AI Voice Dubbing Studio", version="1.0.0")

# Setup directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
OUTPUTS_DIR = os.path.join(BASE_DIR, "dubbing_outputs")

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Shared Pipeline instance
_pipeline_instance = None
def get_pipeline():
    global _pipeline_instance
    if _pipeline_instance is None:
        logger.info("Initializing DubbingPipeline...")
        _pipeline_instance = DubbingPipeline(whisper_model="base")
    return _pipeline_instance

# In-memory Job Store
jobs: Dict[str, Dict[str, Any]] = {}

class VideoInfoRequest(BaseModel):
    url: str

class StartDubbingRequest(BaseModel):
    url: str
    target_langs: List[str]
    voice_start: float = 0.0
    voice_duration: float = 20.0

@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "languages": TARGET_LANGUAGES
    })

@app.post("/api/video-info")
async def get_video_info(payload: VideoInfoRequest):
    """Fetches video thumbnail, title, author, and duration without full download."""
    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="유튜브 링크를 입력해주세요.")

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "success": True,
                "title": info.get("title", "YouTube Video"),
                "uploader": info.get("uploader", "Unknown"),
                "duration": info.get("duration", 0),
                "thumbnail": info.get("thumbnail", ""),
                "description": (info.get("description", "") or "")[:200]
            }
    except Exception as e:
        logger.error(f"Failed to fetch video info: {e}")
        return {
            "success": False,
            "error": f"영상 정보를 불러올 수 없습니다: {str(e)}"
        }

def run_job_thread(job_id: str, url: str, target_langs: List[str], voice_start: float, voice_duration: float):
    job = jobs[job_id]
    job_output_dir = os.path.join(OUTPUTS_DIR, job_id)
    os.makedirs(job_output_dir, exist_ok=True)

    def progress_callback(pct: float, message: str):
        job["progress"] = round(pct * 100, 1)
        job["status_text"] = message
        job["logs"].append(f"[{round(pct*100)}%] {message}")

    try:
        pipeline = get_pipeline()
        results = pipeline.run(
            youtube_url=url,
            target_langs=target_langs,
            voice_start_sec=voice_start,
            voice_duration=voice_duration,
            output_base_dir=job_output_dir,
            progress_callback=progress_callback
        )
        
        # Format paths relative to web root (/outputs/{job_id}/...)
        web_results = {
            "title": results.get("title"),
            "duration": results.get("duration"),
            "voice_sample_url": f"/outputs/{job_id}/my_voice.wav",
            "original_video_url": f"/outputs/{job_id}/original_video.mp4",
            "original_audio_url": f"/outputs/{job_id}/original_audio.wav",
            "subtitles_ko_url": f"/outputs/{job_id}/subtitles_ko.srt",
            "zip_url": f"/outputs/{job_id}/dubbing_results_all.zip",
            "segments": results.get("segments", []),
            "languages": {}
        }

        for lang, data in results.get("languages", {}).items():
            web_results["languages"][lang] = {
                "name": data.get("name"),
                "translated_text": data.get("translated_text"),
                "audio_url": f"/outputs/{job_id}/dubbed_{lang}.wav",
                "video_url": f"/outputs/{job_id}/dubbed_{lang}.mp4" if data.get("video_path") else None,
                "srt_url": f"/outputs/{job_id}/subtitles_{lang}.srt"
            }

        job["state"] = "completed"
        job["progress"] = 100.0
        job["status_text"] = "모든 작업이 성공적으로 완료되었습니다!"
        job["result"] = web_results

    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        logger.error(f"Job {job_id} failed: {err_detail}")
        job["state"] = "failed"
        job["error"] = str(e)
        job["status_text"] = f"오류 발생: {str(e)}"
        job["logs"].append(f"[ERROR] {str(e)}")

@app.post("/api/start-dubbing")
async def start_dubbing(payload: StartDubbingRequest):
    if not payload.url or not payload.url.strip():
        raise HTTPException(status_code=400, detail="유튜브 링크를 입력해주세요.")
    if not payload.target_langs:
        raise HTTPException(status_code=400, detail="최소 1개 이상의 언어를 선택해주세요.")

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "job_id": job_id,
        "state": "running",
        "progress": 0.0,
        "status_text": "더빙 작업 준비 중...",
        "logs": ["더빙 작업을 시작합니다..."],
        "error": None,
        "result": None
    }

    # Run in background thread so the server remains fully responsive
    thread = threading.Thread(
        target=run_job_thread,
        args=(job_id, payload.url.strip(), payload.target_langs, payload.voice_start, payload.voice_duration),
        daemon=True
    )
    thread.start()

    return {"job_id": job_id}

@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="해당 작업을 찾을 수 없습니다.")
    return job

@app.get("/api/download/{job_id}/{filename}")
async def download_file(job_id: str, filename: str):
    file_path = os.path.join(OUTPUTS_DIR, job_id, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다.")
    return FileResponse(file_path, filename=filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)

