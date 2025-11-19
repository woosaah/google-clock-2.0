/**
 * Camera capture component with motion detection
 * Handles PS Eye camera: low-res motion detection + on-demand high-res capture
 */

import { useEffect, useRef, useState } from 'react';
import { wsService } from '../services/websocket';

interface CameraCaptureProps {
  enabled?: boolean;
  motionSensitivity?: number; // 0-100
  motionFps?: number; // frames per second for motion detection
}

const MOTION_THRESHOLD = 20; // Default motion threshold (adjustable)
const LOW_RES = { width: 320, height: 240 };
const HIGH_RES = { width: 640, height: 480 };

export const CameraCapture: React.FC<CameraCaptureProps> = ({
  enabled = true,
  motionSensitivity = 50,
  motionFps = 1,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [previousFrame, setPreviousFrame] = useState<ImageData | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [motionDetected, setMotionDetected] = useState(false);
  const motionCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize camera
  useEffect(() => {
    if (!enabled) return;

    const initCamera = async () => {
      try {
        // Request PS Eye camera access
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: LOW_RES.width,
            height: LOW_RES.height,
            frameRate: motionFps,
          },
          audio: false, // Audio handled by AudioCapture component
        });

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          setCameraActive(true);
          console.log('Camera initialized successfully');
        }
      } catch (error) {
        console.error('Error accessing camera:', error);
        setCameraActive(false);
      }
    };

    initCamera();

    // Cleanup
    return () => {
      if (videoRef.current?.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [enabled, motionFps]);

  // Motion detection loop
  useEffect(() => {
    if (!cameraActive || !enabled) return;

    const checkMotion = () => {
      if (!videoRef.current || !canvasRef.current) return;

      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      // Set canvas size to low-res
      canvas.width = LOW_RES.width;
      canvas.height = LOW_RES.height;

      // Draw current frame
      ctx.drawImage(videoRef.current, 0, 0, LOW_RES.width, LOW_RES.height);
      const currentFrame = ctx.getImageData(0, 0, LOW_RES.width, LOW_RES.height);

      if (previousFrame) {
        const diff = calculateFrameDifference(currentFrame, previousFrame, motionSensitivity);

        if (diff > MOTION_THRESHOLD) {
          setMotionDetected(true);

          // Notify backend via WebSocket
          wsService.send('motion_detected', {
            timestamp: Date.now(),
            confidence: Math.min(100, (diff / MOTION_THRESHOLD) * 100),
          });

          console.log('Motion detected! Difference:', diff);

          // Debounce - wait 5 seconds before detecting again
          setTimeout(() => setMotionDetected(false), 5000);
        }
      }

      setPreviousFrame(currentFrame);
    };

    // Run motion detection at specified FPS
    motionCheckIntervalRef.current = setInterval(checkMotion, 1000 / motionFps);

    return () => {
      if (motionCheckIntervalRef.current) {
        clearInterval(motionCheckIntervalRef.current);
      }
    };
  }, [cameraActive, enabled, previousFrame, motionFps, motionSensitivity]);

  // Listen for backend commands
  useEffect(() => {
    const handleBackendCommand = (command: any) => {
      if (command.type === 'capture_frame') {
        captureHighResFrame(command.data?.resolution || 'high', command.data?.reason);
      }
    };

    wsService.on('command', handleBackendCommand);

    return () => {
      wsService.off('command', handleBackendCommand);
    };
  }, []);

  /**
   * Calculate frame difference for motion detection
   */
  const calculateFrameDifference = (
    current: ImageData,
    previous: ImageData,
    sensitivity: number
  ): number => {
    let diff = 0;
    const pixelCount = current.data.length / 4;

    // Adjust threshold based on sensitivity (0-100)
    const threshold = 30 - (sensitivity / 100) * 20; // Range: 10-30

    for (let i = 0; i < current.data.length; i += 4) {
      // Calculate RGB difference
      const rDiff = Math.abs(current.data[i] - previous.data[i]);
      const gDiff = Math.abs(current.data[i + 1] - previous.data[i + 1]);
      const bDiff = Math.abs(current.data[i + 2] - previous.data[i + 2]);

      const avgDiff = (rDiff + gDiff + bDiff) / 3;

      if (avgDiff > threshold) {
        diff++;
      }
    }

    // Return percentage of pixels that changed
    return (diff / pixelCount) * 100;
  };

  /**
   * Capture high-resolution frame and send to backend
   */
  const captureHighResFrame = async (resolution: string, reason?: string) => {
    if (!videoRef.current) {
      console.error('Video ref not available');
      return;
    }

    try {
      // Temporarily switch to high-res if needed
      const stream = videoRef.current.srcObject as MediaStream;
      const currentSettings = stream.getVideoTracks()[0].getSettings();

      // If already at correct resolution, capture directly
      const targetRes = resolution === 'high' ? HIGH_RES : LOW_RES;

      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      canvas.width = targetRes.width;
      canvas.height = targetRes.height;

      // Draw current frame
      ctx.drawImage(videoRef.current, 0, 0, targetRes.width, targetRes.height);

      // Convert to base64 JPEG
      const imageDataUrl = canvas.toDataURL('image/jpeg', 0.8);
      const imageBase64 = imageDataUrl.split(',')[1]; // Remove "data:image/jpeg;base64,"

      // Send to backend via WebSocket
      wsService.send('camera_frame', {
        image: imageBase64,
        timestamp: Date.now(),
        resolution: `${targetRes.width}x${targetRes.height}`,
        reason: reason || 'unknown',
      });

      console.log(`Captured ${resolution} frame (${targetRes.width}x${targetRes.height}) - Reason: ${reason}`);
    } catch (error) {
      console.error('Error capturing frame:', error);
    }
  };

  return (
    <>
      {/* Hidden video element for camera feed */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{ display: 'none' }}
      />

      {/* Hidden canvas for frame processing */}
      <canvas
        ref={canvasRef}
        style={{ display: 'none' }}
      />

      {/* Debug indicator (can be removed in production) */}
      {process.env.REACT_APP_DEBUG === 'true' && (
        <div
          style={{
            position: 'fixed',
            bottom: '10px',
            left: '10px',
            padding: '5px 10px',
            background: cameraActive ? 'rgba(0, 255, 0, 0.3)' : 'rgba(255, 0, 0, 0.3)',
            color: 'white',
            fontSize: '12px',
            borderRadius: '5px',
            zIndex: 9999,
          }}
        >
          📷 Camera: {cameraActive ? 'Active' : 'Inactive'}
          {motionDetected && ' 🔴 Motion!'}
        </div>
      )}
    </>
  );
};

export default CameraCapture;
