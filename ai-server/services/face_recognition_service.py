"""Face recognition service using face_recognition library."""

import os
import pickle
import logging
import face_recognition
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class FaceRecognitionService:
    """Service for face detection and recognition."""

    def __init__(self):
        self.known_face_encodings: List[np.ndarray] = []
        self.known_face_names: List[str] = []
        self.tolerance = float(os.getenv("FACE_RECOGNITION_TOLERANCE", "0.6"))
        self.model = os.getenv("FACE_DETECTION_MODEL", "hog")  # 'hog' or 'cnn'
        self.min_confidence = float(os.getenv("MIN_FACE_CONFIDENCE", "0.6"))
        self.encodings_file = Path(os.getenv("MODELS_DIR", "./models")) / "face_encodings.pkl"
        self.ready = False

    async def initialize(self):
        """Initialize the service and load existing encodings."""
        try:
            # Create models directory if it doesn't exist
            self.encodings_file.parent.mkdir(parents=True, exist_ok=True)

            # Load existing encodings if available
            if self.encodings_file.exists():
                await self._load_encodings()
                logger.info(f"Loaded {len(self.known_face_names)} face encodings")
            else:
                logger.info("No existing face encodings found")

            self.ready = True
            logger.info("Face recognition service initialized")

        except Exception as e:
            logger.error(f"Error initializing face recognition: {e}")
            self.ready = False

    async def _load_encodings(self):
        """Load face encodings from disk."""
        try:
            with open(self.encodings_file, "rb") as f:
                data = pickle.load(f)
                self.known_face_encodings = data.get("encodings", [])
                self.known_face_names = data.get("names", [])
        except Exception as e:
            logger.error(f"Error loading encodings: {e}")
            self.known_face_encodings = []
            self.known_face_names = []

    async def _save_encodings(self):
        """Save face encodings to disk."""
        try:
            data = {
                "encodings": self.known_face_encodings,
                "names": self.known_face_names
            }
            with open(self.encodings_file, "wb") as f:
                pickle.dump(data, f)
            logger.info("Face encodings saved")
        except Exception as e:
            logger.error(f"Error saving encodings: {e}")

    async def train_person(self, name: str, images: List[np.ndarray]) -> bool:
        """
        Train face recognition with multiple images of a person.

        Args:
            name: Person's name
            images: List of numpy arrays representing images

        Returns:
            True if training successful, False otherwise
        """
        try:
            new_encodings = []

            for i, image in enumerate(images):
                # Convert to RGB if needed
                if len(image.shape) == 2:
                    image = np.stack([image] * 3, axis=-1)
                elif image.shape[2] == 4:
                    image = image[:, :, :3]

                # Find faces in image
                face_locations = face_recognition.face_locations(image, model=self.model)

                if not face_locations:
                    logger.warning(f"No face found in image {i} for {name}")
                    continue

                if len(face_locations) > 1:
                    logger.warning(f"Multiple faces found in image {i} for {name}, using first one")

                # Get face encoding
                face_encodings = face_recognition.face_encodings(image, face_locations)
                if face_encodings:
                    new_encodings.append(face_encodings[0])
                    logger.info(f"Encoded face {i} for {name}")

            if not new_encodings:
                logger.error(f"No valid face encodings found for {name}")
                return False

            # Remove existing encodings for this person
            indices_to_remove = [i for i, n in enumerate(self.known_face_names) if n == name]
            for idx in sorted(indices_to_remove, reverse=True):
                del self.known_face_encodings[idx]
                del self.known_face_names[idx]

            # Add new encodings
            self.known_face_encodings.extend(new_encodings)
            self.known_face_names.extend([name] * len(new_encodings))

            # Save to disk
            await self._save_encodings()

            logger.info(f"Successfully trained {len(new_encodings)} face encodings for {name}")
            return True

        except Exception as e:
            logger.error(f"Error training person: {e}")
            return False

    async def recognize(self, image: np.ndarray) -> Dict:
        """
        Recognize person from image.

        Args:
            image: Numpy array representing the image

        Returns:
            Dictionary with recognition results
        """
        try:
            if not self.known_face_encodings:
                return {
                    "name": "unknown",
                    "confidence": 0.0,
                    "face_locations": [],
                    "message": "No trained faces available"
                }

            # Convert to RGB if needed
            if len(image.shape) == 2:
                image = np.stack([image] * 3, axis=-1)
            elif image.shape[2] == 4:
                image = image[:, :, :3]

            # Find faces in image
            face_locations = face_recognition.face_locations(image, model=self.model)

            if not face_locations:
                return {
                    "name": "none",
                    "confidence": 0.0,
                    "face_locations": [],
                    "message": "No face detected"
                }

            # Get face encodings
            face_encodings = face_recognition.face_encodings(image, face_locations)

            if not face_encodings:
                return {
                    "name": "unknown",
                    "confidence": 0.0,
                    "face_locations": face_locations,
                    "message": "Could not encode face"
                }

            # Use first detected face
            face_encoding = face_encodings[0]
            face_location = face_locations[0]

            # Compare with known faces
            face_distances = face_recognition.face_distance(
                self.known_face_encodings,
                face_encoding
            )

            if len(face_distances) == 0:
                return {
                    "name": "unknown",
                    "confidence": 0.0,
                    "face_locations": [face_location]
                }

            # Find best match
            best_match_index = np.argmin(face_distances)
            best_distance = face_distances[best_match_index]

            # Calculate confidence (inverse of distance)
            confidence = 1.0 - best_distance

            if best_distance <= self.tolerance and confidence >= self.min_confidence:
                name = self.known_face_names[best_match_index]
            else:
                name = "unknown"

            return {
                "name": name,
                "confidence": float(confidence),
                "face_locations": [face_location],
                "distance": float(best_distance)
            }

        except Exception as e:
            logger.error(f"Error recognizing face: {e}")
            return {
                "name": "error",
                "confidence": 0.0,
                "face_locations": [],
                "error": str(e)
            }

    async def detect_faces(self, image: np.ndarray) -> List:
        """
        Detect faces in image without recognition.

        Args:
            image: Numpy array representing the image

        Returns:
            List of face locations [(top, right, bottom, left), ...]
        """
        try:
            # Convert to RGB if needed
            if len(image.shape) == 2:
                image = np.stack([image] * 3, axis=-1)
            elif image.shape[2] == 4:
                image = image[:, :, :3]

            face_locations = face_recognition.face_locations(image, model=self.model)
            return face_locations

        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []

    def is_ready(self) -> bool:
        """Check if service is ready."""
        return self.ready

    async def get_known_persons(self) -> List[str]:
        """Get list of known persons."""
        return list(set(self.known_face_names))

    async def delete_person(self, name: str) -> bool:
        """Delete all face encodings for a person."""
        try:
            indices_to_remove = [i for i, n in enumerate(self.known_face_names) if n == name]

            if not indices_to_remove:
                return False

            for idx in sorted(indices_to_remove, reverse=True):
                del self.known_face_encodings[idx]
                del self.known_face_names[idx]

            await self._save_encodings()
            logger.info(f"Deleted {len(indices_to_remove)} encodings for {name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting person: {e}")
            return False
