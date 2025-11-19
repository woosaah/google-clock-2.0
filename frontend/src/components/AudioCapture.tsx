/**
 * Audio capture component with rolling buffer for wake word detection
 * Handles PS Eye microphone array: continuous buffering + streaming on-demand
 */

import { useEffect, useRef, useState } from 'react';
import { wsService } from '../services/websocket';

interface AudioCaptureProps {
  enabled?: boolean;
  bufferDuration?: number; // seconds to keep in rolling buffer
  chunkSize?: number; // milliseconds per chunk
}

const DEFAULT_BUFFER_DURATION = 3; // 3 seconds
const DEFAULT_CHUNK_SIZE = 100; // 100ms chunks
const SAMPLE_RATE = 16000; // 16kHz - optimal for STT

export const AudioCapture: React.FC<AudioCaptureProps> = ({
  enabled = true,
  bufferDuration = DEFAULT_BUFFER_DURATION,
  chunkSize = DEFAULT_CHUNK_SIZE,
}) => {
  const [isListening, setIsListening] = useState(false);
  const [audioActive, setAudioActive] = useState(false);
  const [isCapturingQuery, setIsCapturingQuery] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioBufferRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const queryTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize audio capture
  useEffect(() => {
    if (!enabled) return;

    const initAudio = async () => {
      try {
        // Request PS Eye microphone access
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1, // Mono (PS Eye has 4-mic array, but we'll use mono for now)
            sampleRate: SAMPLE_RATE,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
          video: false,
        });

        streamRef.current = stream;

        // Create MediaRecorder
        const mediaRecorder = new MediaRecorder(stream, {
          mimeType: 'audio/webm;codecs=opus', // Opus is efficient for voice
        });

        mediaRecorderRef.current = mediaRecorder;

        // Handle audio data chunks
        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            handleAudioChunk(event.data);
          }
        };

        // Start recording in chunks
        mediaRecorder.start(chunkSize);
        setAudioActive(true);
        console.log('Audio capture initialized successfully');
      } catch (error) {
        console.error('Error accessing microphone:', error);
        setAudioActive(false);
      }
    };

    initAudio();

    // Cleanup
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, [enabled, chunkSize]);

  // Listen for backend commands
  useEffect(() => {
    const handleBackendCommand = (command: any) => {
      switch (command.type) {
        case 'start_listening':
          console.log('Backend requested: Start listening for wake word');
          setIsListening(true);
          break;

        case 'stop_listening':
          console.log('Backend requested: Stop listening');
          setIsListening(false);
          break;

        case 'capture_query':
          console.log('Backend requested: Capture voice query');
          captureFullQuery(command.data?.duration || 5);
          break;

        default:
          break;
      }
    };

    wsService.on('command', handleBackendCommand);

    return () => {
      wsService.off('command', handleBackendCommand);
    };
  }, []);

  /**
   * Handle incoming audio chunk
   */
  const handleAudioChunk = (audioBlob: Blob) => {
    // Add to rolling buffer
    audioBufferRef.current.push(audioBlob);

    // Maintain buffer size (keep only last N seconds)
    const maxChunks = Math.ceil((bufferDuration * 1000) / chunkSize);
    if (audioBufferRef.current.length > maxChunks) {
      audioBufferRef.current.shift(); // Remove oldest chunk
    }

    // If actively listening for wake word, stream to backend
    if (isListening && !isCapturingQuery) {
      sendAudioChunk(audioBlob);
    }
  };

  /**
   * Send single audio chunk to backend
   */
  const sendAudioChunk = async (audioBlob: Blob) => {
    try {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64Audio = (reader.result as string).split(',')[1];

        wsService.send('audio_chunk', {
          audio: base64Audio,
          timestamp: Date.now(),
          format: 'webm',
        });
      };
      reader.readAsDataURL(audioBlob);
    } catch (error) {
      console.error('Error sending audio chunk:', error);
    }
  };

  /**
   * Capture full voice query (e.g., after wake word detected)
   */
  const captureFullQuery = (durationSeconds: number) => {
    console.log(`Capturing voice query for ${durationSeconds} seconds...`);
    setIsCapturingQuery(true);

    const captureChunks: Blob[] = [];
    const captureStartTime = Date.now();

    // Capture audio for specified duration
    const captureInterval = setInterval(() => {
      // Add current buffer to capture
      captureChunks.push(...audioBufferRef.current);
      audioBufferRef.current = []; // Clear buffer

      // Check if duration elapsed
      if (Date.now() - captureStartTime >= durationSeconds * 1000) {
        clearInterval(captureInterval);
        finalizeCaptureQuery(captureChunks, durationSeconds);
      }
    }, chunkSize);

    // Safety timeout
    queryTimeoutRef.current = setTimeout(() => {
      clearInterval(captureInterval);
      finalizeCaptureQuery(captureChunks, durationSeconds);
    }, durationSeconds * 1000 + 500); // Extra 500ms buffer
  };

  /**
   * Finalize and send captured query to backend
   */
  const finalizeCaptureQuery = async (chunks: Blob[], duration: number) => {
    console.log(`Finalizing voice query: ${chunks.length} chunks, ${duration}s`);

    try {
      // Combine all chunks into single blob
      const fullAudio = new Blob(chunks, { type: 'audio/webm;codecs=opus' });

      // Convert to base64
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64Audio = (reader.result as string).split(',')[1];

        wsService.send('voice_query', {
          audio: base64Audio,
          duration: duration,
          timestamp: Date.now(),
          format: 'webm',
          size: fullAudio.size,
        });

        console.log(`Voice query sent: ${fullAudio.size} bytes`);
      };
      reader.readAsDataURL(fullAudio);
    } catch (error) {
      console.error('Error finalizing voice query:', error);
    } finally {
      setIsCapturingQuery(false);
    }
  };

  return (
    <>
      {/* Debug indicator (can be removed in production) */}
      {process.env.REACT_APP_DEBUG === 'true' && (
        <div
          style={{
            position: 'fixed',
            bottom: '10px',
            right: '10px',
            padding: '5px 10px',
            background: audioActive
              ? isListening
                ? 'rgba(255, 0, 0, 0.5)' // Red when listening
                : 'rgba(0, 255, 0, 0.3)' // Green when active but not listening
              : 'rgba(255, 255, 255, 0.3)', // Gray when inactive
            color: 'white',
            fontSize: '12px',
            borderRadius: '5px',
            zIndex: 9999,
          }}
        >
          🎤 Mic: {audioActive ? 'Active' : 'Inactive'}
          {isListening && ' 🔴 Listening'}
          {isCapturingQuery && ' 🎙️ Recording Query'}
        </div>
      )}
    </>
  );
};

export default AudioCapture;
