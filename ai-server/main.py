"""AI Server for Google Clock 2.0 - Face Recognition, Voice Processing."""

import logging
import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import base64
from io import BytesIO
from PIL import Image
import numpy as np

# Import services (will create these next)
from services.face_recognition_service import FaceRecognitionService
from services.voice_service import VoiceService

# Logging setup
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Google Clock 2.0 AI Server",
    description="AI processing for face recognition and voice commands",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
face_service = FaceRecognitionService()
voice_service = VoiceService()


# Pydantic models
class FaceTrainRequest(BaseModel):
    person_name: str
    images: List[str]  # Base64 encoded images


class FaceRecognizeRequest(BaseModel):
    image: str  # Base64 encoded image


class VoiceTranscribeRequest(BaseModel):
    audio: str  # Base64 encoded audio
    language: Optional[str] = "en"


class TTSRequest(BaseModel):
    text: str
    rate: Optional[int] = 150
    volume: Optional[float] = 0.9


class OllamaRequest(BaseModel):
    prompt: str
    model: Optional[str] = "llama2"
    context: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting AI Server...")
    await face_service.initialize()
    await voice_service.initialize()
    logger.info("AI Server ready!")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Google Clock 2.0 AI Server",
        "version": "2.0.0",
        "status": "running",
        "capabilities": [
            "face_recognition",
            "face_training",
            "speech_to_text",
            "text_to_speech",
            "wake_word_detection",
            "natural_language_processing"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "face_service": face_service.is_ready(),
        "voice_service": voice_service.is_ready()
    }


# Face Recognition Endpoints

@app.post("/faces/train")
async def train_face(request: FaceTrainRequest):
    """Train face recognition model with person's photos."""
    try:
        # Decode base64 images
        images = []
        for img_b64 in request.images:
            img_data = base64.b64decode(img_b64)
            img = Image.open(BytesIO(img_data))
            images.append(np.array(img))

        # Train the model
        success = await face_service.train_person(request.person_name, images)

        if success:
            return {
                "status": "success",
                "person": request.person_name,
                "samples_trained": len(images)
            }
        else:
            raise HTTPException(status_code=500, detail="Training failed")

    except Exception as e:
        logger.error(f"Error training face: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/faces/recognize")
async def recognize_face(request: FaceRecognizeRequest):
    """Recognize person from image."""
    try:
        # Decode base64 image
        img_data = base64.b64decode(request.image)
        img = Image.open(BytesIO(img_data))
        img_array = np.array(img)

        # Recognize face
        result = await face_service.recognize(img_array)

        return {
            "person": result.get("name", "unknown"),
            "confidence": result.get("confidence", 0.0),
            "face_locations": result.get("face_locations", [])
        }

    except Exception as e:
        logger.error(f"Error recognizing face: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/faces/detect")
async def detect_faces(image: UploadFile = File(...)):
    """Detect faces in image (no recognition)."""
    try:
        img_data = await image.read()
        img = Image.open(BytesIO(img_data))
        img_array = np.array(img)

        faces = await face_service.detect_faces(img_array)

        return {
            "face_count": len(faces),
            "face_locations": faces
        }

    except Exception as e:
        logger.error(f"Error detecting faces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Voice Processing Endpoints

@app.post("/voice/transcribe")
async def transcribe_audio(request: VoiceTranscribeRequest):
    """Transcribe audio to text using Whisper."""
    try:
        # Decode base64 audio
        audio_data = base64.b64decode(request.audio)

        # Transcribe
        transcript = await voice_service.transcribe(
            audio_data,
            language=request.language
        )

        return {
            "transcript": transcript.get("text", ""),
            "language": transcript.get("language", request.language),
            "confidence": transcript.get("confidence", 1.0)
        }

    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/tts")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech."""
    try:
        audio_data = await voice_service.text_to_speech(
            request.text,
            rate=request.rate,
            volume=request.volume
        )

        # Return base64 encoded audio
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')

        return {
            "audio": audio_b64,
            "format": "wav",
            "text": request.text
        }

    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/wake-word")
async def detect_wake_word(audio: UploadFile = File(...)):
    """Detect wake word in audio stream."""
    try:
        audio_data = await audio.read()

        detected = await voice_service.detect_wake_word(audio_data)

        return {
            "detected": detected.get("detected", False),
            "confidence": detected.get("confidence", 0.0),
            "wake_word": detected.get("wake_word", "")
        }

    except Exception as e:
        logger.error(f"Error detecting wake word: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Natural Language Processing (Ollama)

@app.post("/nlp/process")
async def process_natural_language(request: OllamaRequest):
    """Process natural language query using Ollama."""
    try:
        response = await voice_service.process_with_ollama(
            request.prompt,
            model=request.model,
            context=request.context
        )

        return {
            "response": response.get("text", ""),
            "model": request.model,
            "confidence": response.get("confidence", 1.0)
        }

    except Exception as e:
        logger.error(f"Error processing NLP: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("AI_SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("AI_SERVER_PORT", 8000)),
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
