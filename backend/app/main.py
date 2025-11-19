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


# Helper functions
def get_time_of_day() -> str:
    """Get current time of day (morning, afternoon, evening)."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    else:
        return "evening"


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

    # Initialize weather service
    from app.services.weather_service import init_weather_service
    init_weather_service(settings.openweather_api_key)

    # Initialize COLEHUB connection
    from app.services.colehub_service import init_colehub_connection
    init_colehub_connection()

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

            elif message.get("type") == "motion_detected":
                # Motion detected by frontend camera
                logger.info(f"Motion detected: {message.get('data')}")

                # Request high-res frame for face recognition
                await websocket.send_json({
                    "type": "command",
                    "command": "capture_frame",
                    "data": {
                        "resolution": "high",
                        "reason": "face_recognition"
                    }
                })

                # Start listening for wake word
                await websocket.send_json({
                    "type": "command",
                    "command": "start_listening",
                    "data": {
                        "mode": "wake_word"
                    }
                })

            elif message.get("type") == "camera_frame":
                # High-res frame received from frontend
                logger.info("Camera frame received, processing for face recognition...")

                try:
                    # Forward to AI server for face recognition
                    import httpx
                    from app.config import settings

                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.post(
                            f"{settings.ai_server_url}/faces/recognize",
                            json={"image": message.get("data", {}).get("image")}
                        )

                        if response.status_code == 200:
                            result = response.json()
                            logger.info(f"Face recognition result: {result}")

                            # Store detection in database
                            from app.database import Detection, Person
                            db = SessionLocal()
                            try:
                                person_name = result.get("person")

                                # Only save if a person was recognized
                                if person_name and person_name not in ["unknown", "none", "error"]:
                                    # Get or create person
                                    person = db.query(Person).filter(Person.name == person_name).first()

                                    # Check if this is first detection of the day
                                    today = datetime.now().date()
                                    first_today = db.query(Detection).filter(
                                        Detection.person_id == (person.id if person else None),
                                        Detection.detected_at >= today
                                    ).first() is None if person else True

                                    # Create detection record
                                    detection = Detection(
                                        person_id=person.id if person else None,
                                        confidence=result.get("confidence", 0.0),
                                        first_of_day=first_today,
                                        greeted=True  # Will be set to True after showing greeting
                                    )
                                    db.add(detection)
                                    db.commit()
                                    logger.info(f"Detection saved: {person_name} (first of day: {first_today})")

                                    # Trigger greeting only if first detection of the day
                                    if first_today:
                                        await websocket.send_json({
                                            "type": "command",
                                            "command": "show_greeting",
                                            "data": {
                                                "person": person_name,
                                                "confidence": result.get("confidence"),
                                                "time_of_day": get_time_of_day()
                                            }
                                        })
                                    else:
                                        logger.info(f"{person_name} already greeted today, skipping greeting")

                            except Exception as e:
                                logger.error(f"Error saving detection: {e}")
                                db.rollback()
                            finally:
                                db.close()
                        else:
                            logger.error(f"AI server error: {response.status_code}")

                except Exception as e:
                    logger.error(f"Error processing camera frame: {e}")

            elif message.get("type") == "audio_chunk":
                # Audio chunk received for wake word detection
                # Forward to AI server
                try:
                    import httpx
                    from app.config import settings

                    # TODO: Buffer chunks and send to AI server for wake word detection
                    # For now, just log
                    logger.debug("Audio chunk received (wake word detection)")

                except Exception as e:
                    logger.error(f"Error processing audio chunk: {e}")

            elif message.get("type") == "voice_query":
                # Full voice query received
                logger.info("Voice query received, processing with STT...")

                try:
                    import httpx
                    from app.config import settings

                    # Forward to AI server for STT
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            f"{settings.ai_server_url}/voice/transcribe",
                            json={
                                "audio": message.get("data", {}).get("audio"),
                                "language": "en"
                            }
                        )

                        if response.status_code == 200:
                            result = response.json()
                            transcript = result.get("transcript", "")
                            logger.info(f"Transcript: {transcript}")

                            # Process intent
                            # TODO: Implement intent processing
                            intent = "unknown"

                            # Generate response
                            # TODO: Generate proper response with NLP
                            response_text = f"I heard: {transcript}"

                            # Save voice command to database
                            from app.database import VoiceCommand
                            db = SessionLocal()
                            try:
                                voice_cmd = VoiceCommand(
                                    transcript=transcript,
                                    intent=intent,
                                    response=response_text,
                                    confidence=100,  # Whisper doesn't provide confidence
                                    duration_ms=message.get("data", {}).get("duration", 0) * 1000
                                )
                                db.add(voice_cmd)
                                db.commit()
                                logger.info(f"Voice command saved: {transcript}")
                            except Exception as e:
                                logger.error(f"Error saving voice command: {e}")
                                db.rollback()
                            finally:
                                db.close()

                            # Send TTS back to frontend
                            tts_response = await client.post(
                                f"{settings.ai_server_url}/voice/tts",
                                json={"text": response_text}
                            )

                            if tts_response.status_code == 200:
                                tts_data = tts_response.json()
                                await websocket.send_json({
                                    "type": "command",
                                    "command": "speak",
                                    "data": {
                                        "audio": tts_data.get("audio"),
                                        "text": response_text
                                    }
                                })
                        else:
                            logger.error(f"STT error: {response.status_code}")

                except Exception as e:
                    logger.error(f"Error processing voice query: {e}")

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
async def get_weather(
    city: str = "San Francisco",
    country: str = "US",
    units: str = "metric"
):
    """Get current weather."""
    from app.services.weather_service import get_weather_service

    try:
        weather_svc = get_weather_service()
        weather_data = await weather_svc.get_current_weather(city, country, units)

        if weather_data:
            return weather_data
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch weather")

    except Exception as e:
        logger.error(f"Error getting weather: {e}")
        # Return mock data as fallback
        return {
            "temperature": 72,
            "condition": "Sunny",
            "humidity": 45,
            "wind_speed": 10,
            "icon": "01d",
            "mock": True
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


# COLEHUB Integration API

@app.get("/api/colehub/points")
async def get_cole_points():
    """Get Cole's current points and statistics."""
    from app.services.colehub_service import get_colehub_service

    try:
        colehub_svc = get_colehub_service()
        points_data = await colehub_svc.get_cole_points()
        return points_data
    except Exception as e:
        logger.error(f"Error fetching Cole's points: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch points data")


@app.get("/api/colehub/tasks")
async def get_cole_tasks(limit: int = 10):
    """Get Cole's pending tasks."""
    from app.services.colehub_service import get_colehub_service

    try:
        colehub_svc = get_colehub_service()
        tasks = await colehub_svc.get_cole_tasks(limit=limit)
        return {"tasks": tasks, "count": len(tasks)}
    except Exception as e:
        logger.error(f"Error fetching Cole's tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tasks")


@app.get("/api/colehub/achievements")
async def get_cole_achievements(days: int = 7):
    """Get Cole's recent achievements."""
    from app.services.colehub_service import get_colehub_service

    try:
        colehub_svc = get_colehub_service()
        achievements = await colehub_svc.get_recent_achievements(days=days)
        return {"achievements": achievements, "count": len(achievements)}
    except Exception as e:
        logger.error(f"Error fetching achievements: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch achievements")


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
