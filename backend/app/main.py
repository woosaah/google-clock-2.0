"""Main FastAPI application with WebSocket support."""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json

from app.config import settings
from app.database import (
    get_db,
    MediaQueue,
    MediaLibrary,
    Settings as SettingsModel,
    CalendarEvent,
    VoiceCommand,
    Alarm
)

# Logging setup
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Google Clock 2.0 Backend",
    description="Backend API for distributed smart display system",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")


manager = ConnectionManager()


# Pydantic models for API requests/responses
class CastRequest(BaseModel):
    url: str
    type: Optional[str] = "video"  # 'video', 'audio', 'photo'


class MediaPlayRequest(BaseModel):
    path: str


class PlaybackControl(BaseModel):
    action: str  # 'play', 'pause', 'stop', 'next', 'prev'


class SettingUpdate(BaseModel):
    key: str
    value: Dict[str, Any]


class VoiceCommandRequest(BaseModel):
    transcript: str


# Background task for clock updates
async def broadcast_clock_updates():
    """Broadcast time updates every second."""
    while True:
        try:
            current_time = datetime.now().isoformat()
            await manager.broadcast({
                "type": "clock_update",
                "data": {"time": current_time}
            })
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in clock update: {e}")
            await asyncio.sleep(1)


@app.on_event("startup")
async def startup_event():
    """Run startup tasks."""
    logger.info("Starting Google Clock 2.0 Backend...")
    # Start background clock updates
    asyncio.create_task(broadcast_clock_updates())


@app.on_event("shutdown")
async def shutdown_event():
    """Run shutdown tasks."""
    logger.info("Shutting down Google Clock 2.0 Backend...")


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection for real-time communication."""
    await manager.connect(websocket)
    try:
        while True:
            # Receive messages from frontend
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            if message.get("type") == "request_update":
                # Send current state
                await websocket.send_json({
                    "type": "state_update",
                    "data": {
                        "time": datetime.now().isoformat(),
                        "status": "connected"
                    }
                })

            elif message.get("type") == "media_control":
                # Broadcast media control to all clients
                await manager.broadcast({
                    "type": "media_control",
                    "data": message.get("data")
                })

            elif message.get("type") == "voice_audio":
                # Forward audio to AI server for processing
                # TODO: Implement voice processing
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# API Routes

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Google Clock 2.0 Backend",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# Media Queue API

@app.post("/api/cast")
async def cast_media(request: CastRequest, db: Session = Depends(get_db)):
    """Queue remote URL for playback."""
    try:
        # TODO: Extract metadata from URL using yt-dlp
        media_item = MediaQueue(
            url=request.url,
            title=request.url.split("/")[-1],  # Temporary, extract real title
            media_type=request.type,
            status="queued",
            source="remote"
        )

        db.add(media_item)
        db.commit()
        db.refresh(media_item)

        # Broadcast to frontend
        await manager.broadcast({
            "type": "cast_queued",
            "data": {
                "id": media_item.id,
                "title": media_item.title,
                "url": media_item.url,
                "type": media_item.media_type
            }
        })

        return {
            "id": media_item.id,
            "title": media_item.title,
            "status": "queued"
        }

    except Exception as e:
        logger.error(f"Error casting media: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cast/queue")
async def get_queue(db: Session = Depends(get_db)):
    """Get current media queue."""
    queue = db.query(MediaQueue).filter(
        MediaQueue.status.in_(["queued", "playing"])
    ).order_by(MediaQueue.queued_at).all()

    return [
        {
            "id": item.id,
            "url": item.url,
            "title": item.title,
            "type": item.media_type,
            "status": item.status,
            "queued_at": item.queued_at.isoformat()
        }
        for item in queue
    ]


@app.post("/api/cast/control")
async def control_playback(control: PlaybackControl):
    """Control media playback."""
    await manager.broadcast({
        "type": "playback_control",
        "data": {"action": control.action}
    })

    return {"status": "ok", "action": control.action}


@app.delete("/api/cast/queue/{item_id}")
async def remove_from_queue(item_id: int, db: Session = Depends(get_db)):
    """Remove item from queue."""
    item = db.query(MediaQueue).filter(MediaQueue.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()

    await manager.broadcast({
        "type": "queue_updated",
        "data": {"removed_id": item_id}
    })

    return {"status": "ok"}


# Local Media API

@app.get("/api/media/browse")
async def browse_media(path: str = "/videos", db: Session = Depends(get_db)):
    """Browse local media files."""
    # TODO: Scan media directory and return files
    media_files = db.query(MediaLibrary).filter(
        MediaLibrary.file_path.like(f"%{path}%")
    ).all()

    return [
        {
            "id": item.id,
            "filename": item.filename,
            "type": item.media_type,
            "size": item.file_size,
            "duration": item.duration,
            "thumbnail": item.thumbnail_path
        }
        for item in media_files
    ]


@app.post("/api/media/play")
async def play_local_media(request: MediaPlayRequest, db: Session = Depends(get_db)):
    """Play local media file."""
    media_item = db.query(MediaLibrary).filter(
        MediaLibrary.file_path == request.path
    ).first()

    if not media_item:
        raise HTTPException(status_code=404, detail="Media file not found")

    # Update play count
    media_item.play_count += 1
    media_item.last_played = datetime.now()
    db.commit()

    # Broadcast to frontend
    await manager.broadcast({
        "type": "media_ready",
        "data": {
            "id": media_item.id,
            "path": media_item.file_path,
            "title": media_item.filename,
            "type": media_item.media_type,
            "stream_url": f"/api/media/stream/{media_item.id}"
        }
    })

    return {
        "id": media_item.id,
        "stream_url": f"/api/media/stream/{media_item.id}"
    }


@app.get("/api/media/stream/{media_id}")
async def stream_media(media_id: int, db: Session = Depends(get_db)):
    """Stream media file."""
    media_item = db.query(MediaLibrary).filter(MediaLibrary.id == media_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="Media not found")

    # TODO: Implement proper streaming with range requests
    return FileResponse(media_item.file_path)


# Settings API

@app.get("/api/settings")
async def get_settings(db: Session = Depends(get_db)):
    """Get all settings."""
    settings_list = db.query(SettingsModel).all()
    return {
        setting.key: setting.value
        for setting in settings_list
    }


@app.get("/api/settings/{key}")
async def get_setting(key: str, db: Session = Depends(get_db)):
    """Get specific setting."""
    setting = db.query(SettingsModel).filter(SettingsModel.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return {key: setting.value}


@app.put("/api/settings")
async def update_setting(update: SettingUpdate, db: Session = Depends(get_db)):
    """Update a setting."""
    setting = db.query(SettingsModel).filter(SettingsModel.key == update.key).first()

    if setting:
        setting.value = update.value
        setting.updated_at = datetime.now()
    else:
        setting = SettingsModel(key=update.key, value=update.value)
        db.add(setting)

    db.commit()

    # Broadcast setting change
    await manager.broadcast({
        "type": "settings_updated",
        "data": {update.key: update.value}
    })

    return {"status": "ok", "key": update.key}


# Weather API

@app.get("/api/weather")
async def get_weather():
    """Get current weather."""
    # TODO: Implement OpenWeatherMap API integration
    return {
        "temperature": 72,
        "condition": "Sunny",
        "humidity": 45,
        "wind_speed": 10,
        "icon": "01d"
    }


# Calendar API

@app.get("/api/calendar/events")
async def get_calendar_events(db: Session = Depends(get_db)):
    """Get today's calendar events."""
    # TODO: Implement Google Calendar API integration
    today = datetime.now().date()
    events = db.query(CalendarEvent).filter(
        CalendarEvent.start_time >= today
    ).order_by(CalendarEvent.start_time).limit(10).all()

    return [
        {
            "id": event.id,
            "summary": event.summary,
            "start": event.start_time.isoformat(),
            "end": event.end_time.isoformat(),
            "all_day": event.all_day,
            "location": event.location
        }
        for event in events
    ]


# Voice Assistant API

@app.post("/api/voice/process")
async def process_voice_command(command: VoiceCommandRequest, db: Session = Depends(get_db)):
    """Process voice command."""
    # TODO: Send to AI server for processing
    # For now, just log it
    voice_cmd = VoiceCommand(
        transcript=command.transcript,
        intent="unknown",
        response="Voice processing not yet implemented"
    )
    db.add(voice_cmd)
    db.commit()

    return {
        "transcript": command.transcript,
        "response": "Voice processing coming soon!"
    }


# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
