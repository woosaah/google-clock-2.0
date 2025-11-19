/**
 * Unified media player for video, audio, and photos
 * Fullscreen playback with transport controls
 */

import React, { useRef, useState, useEffect } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import ReactPlayer from 'react-player';

interface MediaPlayerProps {
  show: boolean;
  mediaType: 'video' | 'audio' | 'photo';
  url: string;
  title?: string;
  onEnded?: () => void;
  onClose?: () => void;
  autoPlay?: boolean;
}

const PlayerContainer = styled(motion.div)`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #000;
  z-index: 999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
`;

const VideoWrapper = styled.div`
  width: 100%;
  height: 100%;
  position: relative;
`;

const AudioWrapper = styled.div`
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
`;

const PhotoWrapper = styled.div`
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
`;

const Photo = styled.img`
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
`;

const ClockOverlay = styled.div`
  position: fixed;
  top: 2rem;
  left: 2rem;
  font-size: 2rem;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 300;
  z-index: 1001;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
`;

const ControlsOverlay = styled(motion.div)`
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.8), transparent);
  padding: 2rem;
  z-index: 1001;
`;

const Controls = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 1200px;
  margin: 0 auto;
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
  cursor: pointer;
  position: relative;
`;

const Progress = styled.div<{ progress: number }>`
  width: ${props => props.progress}%;
  height: 100%;
  background: #667eea;
  border-radius: 3px;
  transition: width 0.1s ease;
`;

const ButtonRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 1rem;
  align-items: center;
`;

const Button = styled.button`
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.3);
    transform: scale(1.05);
  }

  &:active {
    transform: scale(0.95);
  }
`;

const VolumeSlider = styled.input`
  width: 100px;
`;

const Title = styled.div`
  font-size: 1.2rem;
  color: white;
  font-weight: 500;
`;

const TimeDisplay = styled.div`
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.9rem;
  min-width: 120px;
  text-align: right;
`;

const AudioTitle = styled.h2`
  font-size: 3rem;
  color: white;
  margin-bottom: 2rem;
  text-align: center;
`;

const AudioIcon = styled.div`
  font-size: 8rem;
  margin-bottom: 2rem;
`;

export const MediaPlayer: React.FC<MediaPlayerProps> = ({
  show,
  mediaType,
  url,
  title,
  onEnded,
  onClose,
  autoPlay = true,
}) => {
  const playerRef = useRef<ReactPlayer>(null);
  const [playing, setPlaying] = useState(autoPlay);
  const [volume, setVolume] = useState(0.7);
  const [played, setPlayed] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showControls, setShowControls] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());

  // Update clock every second
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Auto-hide controls after 5 seconds
  useEffect(() => {
    if (showControls && playing) {
      const timer = setTimeout(() => {
        setShowControls(false);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [showControls, playing]);

  const handlePlayPause = () => {
    setPlaying(!playing);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setVolume(parseFloat(e.target.value));
  };

  const handleProgress = (state: any) => {
    setPlayed(state.played);
  };

  const handleDuration = (dur: number) => {
    setDuration(dur);
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const bounds = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - bounds.left;
    const percentage = x / bounds.width;
    playerRef.current?.seekTo(percentage);
  };

  const handleEnded = () => {
    setPlaying(false);
    if (onEnded) {
      onEnded();
    }
  };

  const handleClose = () => {
    setPlaying(false);
    if (onClose) {
      onClose();
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleContainerClick = () => {
    if (mediaType === 'video') {
      setShowControls(!showControls);
    }
  };

  if (!show) return null;

  return (
    <AnimatePresence>
      <PlayerContainer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={handleContainerClick}
      >
        {/* Clock overlay (always visible in corner) */}
        <ClockOverlay>
          {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </ClockOverlay>

        {/* Media content */}
        {mediaType === 'video' && (
          <VideoWrapper>
            <ReactPlayer
              ref={playerRef}
              url={url}
              playing={playing}
              volume={volume}
              width="100%"
              height="100%"
              onProgress={handleProgress}
              onDuration={handleDuration}
              onEnded={handleEnded}
              controls={false}
            />
          </VideoWrapper>
        )}

        {mediaType === 'audio' && (
          <AudioWrapper>
            <AudioIcon>🎵</AudioIcon>
            <AudioTitle>{title || 'Now Playing'}</AudioTitle>
            <ReactPlayer
              ref={playerRef}
              url={url}
              playing={playing}
              volume={volume}
              width="0"
              height="0"
              onProgress={handleProgress}
              onDuration={handleDuration}
              onEnded={handleEnded}
            />
          </AudioWrapper>
        )}

        {mediaType === 'photo' && (
          <PhotoWrapper>
            <Photo src={url} alt={title || 'Photo'} />
          </PhotoWrapper>
        )}

        {/* Transport controls */}
        {showControls && (
          <ControlsOverlay
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0 }}
            onClick={(e) => e.stopPropagation()}
          >
            <Controls>
              {(mediaType === 'video' || mediaType === 'audio') && (
                <ProgressBar onClick={handleSeek}>
                  <Progress progress={played * 100} />
                </ProgressBar>
              )}

              <ButtonRow>
                <ButtonGroup>
                  <Button onClick={handlePlayPause}>
                    {playing ? '⏸️ Pause' : '▶️ Play'}
                  </Button>

                  <Button onClick={handleClose}>
                    🏠 Back to Clock
                  </Button>
                </ButtonGroup>

                <Title>{title || url.split('/').pop()}</Title>

                <ButtonGroup>
                  {(mediaType === 'video' || mediaType === 'audio') && (
                    <>
                      <span style={{ color: 'white' }}>🔊</span>
                      <VolumeSlider
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={volume}
                        onChange={handleVolumeChange}
                      />
                    </>
                  )}

                  {(mediaType === 'video' || mediaType === 'audio') && (
                    <TimeDisplay>
                      {formatTime(played * duration)} / {formatTime(duration)}
                    </TimeDisplay>
                  )}
                </ButtonGroup>
              </ButtonRow>
            </Controls>
          </ControlsOverlay>
        )}
      </PlayerContainer>
    </AnimatePresence>
  );
};

export default MediaPlayer;
