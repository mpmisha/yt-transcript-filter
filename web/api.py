from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import json
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="yt-transcript-filter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class FetchRequest(BaseModel):
    url: str
    lang: str = "en"
    limit: Optional[int] = Field(default=None, ge=1)


class FilterRequest(BaseModel):
    topic: str
    threshold: int = Field(default=5, ge=0, le=10)
    output_dir: str = "./transcripts"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/fetch-transcripts")
async def fetch_transcripts(req: FetchRequest):
    if not req.url.strip():
        return JSONResponse(status_code=400, content={"detail": "URL is required"})

    def event_stream():
        try:
            from src.service import fetch_channel_transcripts
            for event in fetch_channel_transcripts(req.url, req.lang, limit=req.limit):
                yield f"data: {json.dumps(event)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'event': 'error', 'detail': str(e)})}\n\n"
        except Exception:
            logging.getLogger(__name__).exception("Unhandled error in fetch-transcripts stream")
            yield f"data: {json.dumps({'event': 'error', 'detail': 'Internal server error'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/transcripts")
async def list_transcripts():
    from src.storage import load_index

    try:
        index = load_index("./transcripts")
    except FileNotFoundError:
        return {"videos": [], "total": 0, "with_transcript": 0}

    videos = [
        {
            "video_id": entry["video_id"],
            "title": entry["title"],
            "url": entry["url"],
            "duration": entry.get("duration"),
            "upload_date": entry.get("upload_date"),
            "has_transcript": entry.get("has_transcript", False),
            "transcript_source": entry.get(
                "transcript_source",
                "youtube" if entry.get("has_transcript") else None,
            ),
        }
        for entry in index
    ]

    with_transcript = sum(1 for video in videos if video["has_transcript"])

    return {
        "videos": videos,
        "total": len(videos),
        "with_transcript": with_transcript,
    }


@app.get("/api/transcripts/{video_id}")
async def get_transcript(video_id: str):
    from src.storage import load_index, load_transcript

    try:
        index = load_index("./transcripts")
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"detail": "Transcript not found"})

    entry = next((e for e in index if e["video_id"] == video_id), None)
    if entry is None:
        return JSONResponse(status_code=404, content={"detail": "Transcript not found"})

    try:
        content = load_transcript("./transcripts", entry["file"])
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"detail": "Transcript not found"})

    return {
        "video_id": video_id,
        "title": entry["title"],
        "content": content,
    }


@app.post("/api/filter-by-topic")
async def filter_by_topic_endpoint(req: FilterRequest):
    if not req.topic.strip():
        return JSONResponse(status_code=400, content={"detail": "Topic is required"})

    def event_stream():
        try:
            from src.llm_filter import filter_by_topic

            for event in filter_by_topic(req.output_dir, req.topic.strip(), threshold=req.threshold):
                yield f"data: {json.dumps(event)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'event': 'filter_error', 'detail': str(e)})}\n\n"
        except Exception:
            logging.getLogger(__name__).exception("Unhandled error in filter-by-topic stream")
            yield f"data: {json.dumps({'event': 'filter_error', 'detail': 'Internal server error'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
