/**
 * PersonGreeting overlay component
 * Shows animated greeting when person is detected
 */

import React, { useEffect, useState } from 'react';
import styled, { keyframes } from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';

interface PersonGreetingProps {
  show: boolean;
  person: string;
  confidence?: number;
  timeOfDay: 'morning' | 'afternoon' | 'evening';
  customInfo?: string;
  onDismiss: () => void;
  autoDismissDelay?: number; // milliseconds
}

const fadeIn = keyframes`
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

const Overlay = styled(motion.div)`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  cursor: pointer;
`;

const GreetingCard = styled(motion.div)`
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.95) 0%, rgba(118, 75, 162, 0.95) 100%);
  border-radius: 30px;
  padding: 3rem 4rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  text-align: center;
  max-width: 600px;
  color: white;
  cursor: default;
`;

const GreetingText = styled.h1`
  font-size: 3rem;
  font-weight: 300;
  margin: 0 0 1rem 0;
  line-height: 1.2;

  @media (max-width: 768px) {
    font-size: 2rem;
  }
`;

const PersonName = styled.span`
  font-weight: 600;
  background: linear-gradient(90deg, #ffd700, #ffed4e);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
`;

const SubText = styled.div`
  font-size: 1.5rem;
  opacity: 0.9;
  margin-top: 1rem;
  font-weight: 300;

  @media (max-width: 768px) {
    font-size: 1.2rem;
  }
`;

const Confidence = styled.div`
  font-size: 0.9rem;
  opacity: 0.6;
  margin-top: 1.5rem;
`;

const DismissHint = styled.div`
  font-size: 0.8rem;
  opacity: 0.5;
  margin-top: 2rem;
  animation: ${fadeIn} 0.5s ease-in-out;
  animation-delay: 2s;
  animation-fill-mode: both;
`;

export const PersonGreeting: React.FC<PersonGreetingProps> = ({
  show,
  person,
  confidence,
  timeOfDay,
  customInfo,
  onDismiss,
  autoDismissDelay = 5000,
}) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (show) {
      setIsVisible(true);

      // Auto-dismiss after delay
      const timer = setTimeout(() => {
        handleDismiss();
      }, autoDismissDelay);

      return () => clearTimeout(timer);
    }
  }, [show, autoDismissDelay]);

  const handleDismiss = () => {
    setIsVisible(false);
    setTimeout(() => {
      onDismiss();
    }, 300); // Wait for exit animation
  };

  const getGreeting = () => {
    switch (timeOfDay) {
      case 'morning':
        return 'Good morning';
      case 'afternoon':
        return 'Good afternoon';
      case 'evening':
        return 'Good evening';
      default:
        return 'Hello';
    }
  };

  const getTimeEmoji = () => {
    switch (timeOfDay) {
      case 'morning':
        return '☀️';
      case 'afternoon':
        return '🌤️';
      case 'evening':
        return '🌙';
      default:
        return '👋';
    }
  };

  if (!show) return null;

  return (
    <AnimatePresence>
      {isVisible && (
        <Overlay
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          onClick={handleDismiss}
        >
          <GreetingCard
            initial={{ scale: 0.8, opacity: 0, y: 50 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.8, opacity: 0, y: -50 }}
            transition={{
              type: 'spring',
              damping: 20,
              stiffness: 300,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <GreetingText>
              {getGreeting()},{' '}
              <PersonName>{person}</PersonName>! {getTimeEmoji()}
            </GreetingText>

            {customInfo && (
              <SubText>{customInfo}</SubText>
            )}

            {confidence && confidence > 0 && (
              <Confidence>
                Recognition confidence: {Math.round(confidence * 100)}%
              </Confidence>
            )}

            <DismissHint>
              Tap anywhere to dismiss
            </DismissHint>
          </GreetingCard>
        </Overlay>
      )}
    </AnimatePresence>
  );
};

export default PersonGreeting;
