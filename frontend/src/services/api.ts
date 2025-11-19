/**
 * API service for REST calls to backend.
 */

import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:5000';

class APIService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error.message);
        return Promise.reject(error);
      }
    );
  }

  // Health & Status
  async healthCheck() {
    return this.client.get('/api/health');
  }

  // Media Queue
  async castMedia(url: string, type: 'video' | 'audio' | 'photo' = 'video') {
    return this.client.post('/api/cast', { url, type });
  }

  async getQueue() {
    return this.client.get('/api/cast/queue');
  }

  async controlPlayback(action: 'play' | 'pause' | 'stop' | 'next' | 'prev') {
    return this.client.post('/api/cast/control', { action });
  }

  async removeFromQueue(itemId: number) {
    return this.client.delete(`/api/cast/queue/${itemId}`);
  }

  // Local Media
  async browseMedia(path: string = '/videos') {
    return this.client.get('/api/media/browse', { params: { path } });
  }

  async playLocalMedia(path: string) {
    return this.client.post('/api/media/play', { path });
  }

  // Settings
  async getSettings() {
    return this.client.get('/api/settings');
  }

  async getSetting(key: string) {
    return this.client.get(`/api/settings/${key}`);
  }

  async updateSetting(key: string, value: any) {
    return this.client.put('/api/settings', { key, value });
  }

  // Weather
  async getWeather() {
    return this.client.get('/api/weather');
  }

  // Calendar
  async getCalendarEvents() {
    return this.client.get('/api/calendar/events');
  }

  // Voice
  async processVoiceCommand(transcript: string) {
    return this.client.post('/api/voice/process', { transcript });
  }

  // Person Detection
  async trainFace(personName: string, images: string[]) {
    return this.client.post('/api/faces/train', {
      person_name: personName,
      images,
    });
  }

  async getDetections(since?: string) {
    return this.client.get('/api/faces/detections', {
      params: since ? { since } : {},
    });
  }

  // API Integrations
  async createAPIIntegration(config: any) {
    return this.client.post('/api/integrations/api', config);
  }

  async getAPIIntegrations() {
    return this.client.get('/api/integrations/api');
  }

  async testAPIIntegration(id: number) {
    return this.client.post(`/api/integrations/api/${id}/test`);
  }

  async deleteAPIIntegration(id: number) {
    return this.client.delete(`/api/integrations/api/${id}`);
  }

  // Response Rules
  async createRule(rule: any) {
    return this.client.post('/api/rules/create', rule);
  }

  async getRules() {
    return this.client.get('/api/rules');
  }

  async toggleRule(id: number, enabled: boolean) {
    return this.client.put(`/api/rules/${id}/toggle`, { enabled });
  }

  // Dashboard Data
  async getDashboardData(timerange: string = '24h') {
    return this.client.get('/api/dashboard/data', {
      params: { timerange },
    });
  }
}

export const apiService = new APIService();
export default apiService;
