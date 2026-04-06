from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import json
import logging

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
