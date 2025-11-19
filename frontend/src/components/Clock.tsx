/**
 * Clock component - displays current time
 */

import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { format } from 'date-fns';
import { ClockProps } from '../types';

const ClockContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
`;

const TimeDisplay = styled.div`
  font-size: 8rem;
  font-weight: 300;
  letter-spacing: -0.05em;
  line-height: 1;

  @media (max-width: 1024px) {
    font-size: 6rem;
  }

  @media (max-width: 768px) {
    font-size: 4rem;
  }
`;

const DateDisplay = styled.div`
  font-size: 2rem;
  font-weight: 300;
  margin-top: 1rem;
  opacity: 0.8;

  @media (max-width: 768px) {
    font-size: 1.5rem;
  }
`;

export const Clock: React.FC<ClockProps> = ({
  format: clockFormat = '24hr',
  showSeconds = true,
}) => {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const getTimeFormat = () => {
    if (clockFormat === '12hr') {
      return showSeconds ? 'h:mm:ss a' : 'h:mm a';
    }
    return showSeconds ? 'HH:mm:ss' : 'HH:mm';
  };

  const timeFormat = getTimeFormat();
  const dateFormat = 'EEEE, MMMM d, yyyy';

  return (
    <ClockContainer>
      <TimeDisplay>
        {format(currentTime, timeFormat)}
      </TimeDisplay>
      <DateDisplay>
        {format(currentTime, dateFormat)}
      </DateDisplay>
    </ClockContainer>
  );
};

export default Clock;
