"""Voice processing service for wake word, STT, TTS, and NLP."""

import os
import logging
import io
import wave
import tempfile
from typing import Dict, Optional
import httpx
import numpy as np

logger = logging.getLogger(__name__)


class VoiceService:
    """Service for voice processing."""

    def __init__(self):
        self.whisper_model = os.getenv("WHISPER_MODEL", "base")
        self.whisper_device = os.getenv("WHISPER_DEVICE", "cpu")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama2")
        self.wake_word = os.getenv("WAKE_WORD", "hey_google")
        self.wake_word_engine = os.getenv("WAKE_WORD_ENGINE", "porcupine")
        self.ready = False
        self.whisper = None
        self.tts_engine = None
        self.porcupine = None

    async def initialize(self):
        """Initialize voice processing services."""
        try:
            # Initialize Whisper for STT
            await self._init_whisper()

            # Initialize TTS
            await self._init_tts()

            # Initialize wake word detection
            await self._init_wake_word()

            self.ready = True
            logger.info("Voice service initialized")

        except Exception as e:
            logger.error(f"Error initializing voice service: {e}")
            self.ready = False

    async def _init_whisper(self):
        """Initialize Whisper for speech-to-text."""
        try:
            import whisper
            self.whisper = whisper.load_model(
                self.whisper_model,
                device=self.whisper_device
            )
            logger.info(f"Whisper model '{self.whisper_model}' loaded")
        except Exception as e:
            logger.error(f"Error loading Whisper: {e}")
            logger.warning("STT will not be available")
            self.whisper = None

    async def _init_tts(self):
        """Initialize text-to-speech engine."""
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()

            # Configure TTS
            rate = int(os.getenv("TTS_RATE", "150"))
            volume = float(os.getenv("TTS_VOLUME", "0.9"))

            self.tts_engine.setProperty('rate', rate)
            self.tts_engine.setProperty('volume', volume)

            logger.info("TTS engine initialized")
        except Exception as e:
            logger.error(f"Error initializing TTS: {e}")
            logger.warning("TTS will not be available")
            self.tts_engine = None

    async def _init_wake_word(self):
        """Initialize wake word detection."""
        try:
            if self.wake_word_engine == "porcupine":
                import pvporcupine
                access_key = os.getenv("PORCUPINE_ACCESS_KEY")

                if not access_key:
                    logger.warning("No Porcupine access key provided")
                    return

                self.porcupine = pvporcupine.create(
                    access_key=access_key,
                    keywords=[self.wake_word]
                )
                logger.info(f"Porcupine wake word detection initialized for '{self.wake_word}'")

            else:
                logger.warning(f"Wake word engine '{self.wake_word_engine}' not implemented")

        except Exception as e:
            logger.error(f"Error initializing wake word: {e}")
            logger.warning("Wake word detection will not be available")
            self.porcupine = None

    async def transcribe(self, audio_data: bytes, language: str = "en") -> Dict:
        """
        Transcribe audio to text using Whisper.

        Args:
            audio_data: Audio data in bytes
            language: Language code (default: en)

        Returns:
            Dictionary with transcript and metadata
        """
        try:
            if not self.whisper:
                return {
                    "text": "",
                    "error": "Whisper not initialized"
                }

            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name

            # Transcribe
            result = self.whisper.transcribe(
                temp_path,
                language=language,
                fp16=False if self.whisper_device == "cpu" else True
            )

            # Clean up temp file
            os.unlink(temp_path)

            return {
                "text": result.get("text", ""),
                "language": result.get("language", language),
                "confidence": 1.0  # Whisper doesn't provide confidence
            }

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return {
                "text": "",
                "error": str(e)
            }

    async def text_to_speech(self, text: str, rate: int = 150, volume: float = 0.9) -> bytes:
        """
        Convert text to speech.

        Args:
            text: Text to convert
            rate: Speech rate (words per minute)
            volume: Volume (0.0 to 1.0)

        Returns:
            Audio data as bytes
        """
        try:
            if not self.tts_engine:
                raise Exception("TTS engine not initialized")

            # Configure
            self.tts_engine.setProperty('rate', rate)
            self.tts_engine.setProperty('volume', volume)

            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name

            self.tts_engine.save_to_file(text, temp_path)
            self.tts_engine.runAndWait()

            # Read audio data
            with open(temp_path, "rb") as f:
                audio_data = f.read()

            # Clean up
            os.unlink(temp_path)

            return audio_data

        except Exception as e:
            logger.error(f"Error generating TTS: {e}")
            raise

    async def detect_wake_word(self, audio_data: bytes) -> Dict:
        """
        Detect wake word in audio.

        Args:
            audio_data: Audio data in bytes

        Returns:
            Dictionary with detection result
        """
        try:
            if not self.porcupine:
                return {
                    "detected": False,
                    "error": "Wake word detection not initialized"
                }

            # Convert audio data to PCM frames
            # This is a simplified version - you'll need to handle audio format conversion
            # based on your actual audio input format

            # For now, return a placeholder
            # TODO: Implement proper audio processing for wake word detection

            return {
                "detected": False,
                "confidence": 0.0,
                "wake_word": self.wake_word,
                "message": "Wake word detection needs audio stream processing"
            }

        except Exception as e:
            logger.error(f"Error detecting wake word: {e}")
            return {
                "detected": False,
                "error": str(e)
            }

    async def process_with_ollama(
        self,
        prompt: str,
        model: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict:
        """
        Process natural language query using Ollama.

        Args:
            prompt: User's query
            model: Model to use (default: from env)
            context: Additional context

        Returns:
            Dictionary with response
        """
        try:
            model_name = model or self.ollama_model

            # Prepare prompt with context if provided
            full_prompt = prompt
            if context:
                full_prompt = f"Context: {context}\n\nQuery: {prompt}"

            # Call Ollama API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": full_prompt,
                        "stream": False
                    }
                )

                if response.status_code != 200:
                    raise Exception(f"Ollama API error: {response.status_code}")

                result = response.json()

                return {
                    "text": result.get("response", ""),
                    "model": model_name,
                    "confidence": 1.0
                }

        except Exception as e:
            logger.error(f"Error processing with Ollama: {e}")
            return {
                "text": "",
                "error": str(e)
            }

    def is_ready(self) -> bool:
        """Check if service is ready."""
        return self.ready

    async def get_status(self) -> Dict:
        """Get service status."""
        return {
            "ready": self.ready,
            "whisper_available": self.whisper is not None,
            "tts_available": self.tts_engine is not None,
            "wake_word_available": self.porcupine is not None,
            "whisper_model": self.whisper_model,
            "ollama_host": self.ollama_host,
            "ollama_model": self.ollama_model
        }
