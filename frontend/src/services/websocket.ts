/**
 * WebSocket service for real-time communication with backend.
 */

import { io, Socket } from 'socket.io-client';

type MessageHandler = (data: any) => void;

class WebSocketService {
  private socket: Socket | null = null;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000;

  connect(url: string) {
    if (this.socket?.connected) {
      console.log('WebSocket already connected');
      return;
    }

    console.log(`Connecting to WebSocket: ${url}`);

    this.socket = io(url, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: this.reconnectDelay,
      reconnectionAttempts: this.maxReconnectAttempts,
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connection_status', { connected: true });
    });

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      this.emit('connection_status', { connected: false });
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
      this.emit('connection_error', { error, attempts: this.reconnectAttempts });
    });

    // Listen for all events from server
    this.socket.onAny((event, data) => {
      console.log(`WebSocket event: ${event}`, data);
      this.emit(event, data);
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  send(event: string, data: any) {
    if (!this.socket?.connected) {
      console.warn('WebSocket not connected, cannot send message');
      return;
    }

    this.socket.emit(event, data);
  }

  on(event: string, handler: MessageHandler) {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, []);
    }
    this.handlers.get(event)!.push(handler);
  }

  off(event: string, handler?: MessageHandler) {
    if (!handler) {
      this.handlers.delete(event);
      return;
    }

    const handlers = this.handlers.get(event);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index !== -1) {
        handlers.splice(index, 1);
      }
    }
  }

  private emit(event: string, data: any) {
    const handlers = this.handlers.get(event);
    if (handlers) {
      handlers.forEach(handler => handler(data));
    }
  }

  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }
}

export const wsService = new WebSocketService();
export default wsService;
