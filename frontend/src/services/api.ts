// API client for backend communication
import axios from 'axios';
import type {
  Exception, Shipment, Decision, DemoCase, ExceptionStats, DemoMode, DemoStatus, TimelineEvent,
  TransportLiveData, TransportDashboardData,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Exception API
export const exceptionAPI = {
  getAll: async (): Promise<Exception[]> => {
    const response = await api.get('/exceptions');
    return response.data;
  },

  getById: async (exceptionId: string): Promise<Exception> => {
    const response = await api.get(`/exceptions/${exceptionId}`);
    return response.data;
  },

  getTimeline: async (exceptionId: string): Promise<{ timeline: TimelineEvent[] }> => {
    const response = await api.get(`/exceptions/${exceptionId}/timeline`);
    return response.data;
  },

  approve: async (exceptionId: string, decision: string, notes: string, approvedBy: string) => {
    const response = await api.post(`/exceptions/${exceptionId}/approve`, {
      decision,
      notes,
      approved_by: approvedBy,
    });
    return response.data;
  },

  getStats: async (): Promise<ExceptionStats> => {
    const response = await api.get('/exceptions/summary/stats');
    return response.data;
  },
};

// Shipment API
export const shipmentAPI = {
  getAll: async (): Promise<Shipment[]> => {
    const response = await api.get('/shipments');
    return response.data;
  },

  getById: async (shipmentId: string): Promise<Shipment> => {
    const response = await api.get(`/shipments/${shipmentId}`);
    return response.data;
  },

  getTimeline: async (shipmentId: string): Promise<{ timeline: TimelineEvent[] }> => {
    const response = await api.get(`/shipments/${shipmentId}/timeline`);
    return response.data;
  },

  getStatus: async (shipmentId: string) => {
    const response = await api.get(`/shipments/${shipmentId}/status`);
    return response.data;
  },
};

// Decision API
export const decisionAPI = {
  get: async (exceptionId: string): Promise<Decision> => {
    const response = await api.get(`/decisions/${exceptionId}`);
    return response.data;
  },

  generate: async (exceptionId: string): Promise<Decision> => {
    const response = await api.post(`/decisions/${exceptionId}/generate`);
    return response.data;
  },
};

// Demo API
export const demoAPI = {
  start: async (mode: DemoMode) => {
    const response = await api.post('/demo/start', { mode });
    return response.data;
  },

  pause: async () => {
    const response = await api.post('/demo/pause');
    return response.data;
  },

  resume: async () => {
    const response = await api.post('/demo/resume');
    return response.data;
  },

  reset: async () => {
    const response = await api.post('/demo/reset');
    return response.data;
  },

  nextStep: async () => {
    const response = await api.post('/demo/next-step');
    return response.data;
  },

  getStatus: async (): Promise<DemoStatus> => {
    const response = await api.get('/demo/status');
    return response.data;
  },

  getCases: async (): Promise<{ total_cases: number; cases: DemoCase[] }> => {
    const response = await api.get('/demo/cases');
    return response.data;
  },
};

// Live transport simulator API (air / road / sea)
const normalizeLive = (data: any, tasksKey: string): TransportLiveData => ({
  simulator: data.simulator,
  tasks_total: data[tasksKey]?.total_in_db ?? 0,
  by_status: data[tasksKey]?.by_status ?? {},
  open_exceptions: data.open_exceptions ?? [],
  recent_events: data.recent_events ?? [],
});

const normalizeDashboard = (data: any): TransportDashboardData => data;

export const airAPI = {
  getLive: async (): Promise<TransportLiveData> => {
    const response = await api.get('/air/live');
    return normalizeLive(response.data, 'flights');
  },
  getDashboard: async (): Promise<TransportDashboardData> => {
    const response = await api.get('/air/dashboard');
    return normalizeDashboard(response.data);
  },
  control: async (action: string, speed?: number) => {
    const response = await api.post('/air/sim/control', { action, speed });
    return response.data;
  },
};

export const roadAPI = {
  getLive: async (): Promise<TransportLiveData> => {
    const response = await api.get('/road/live');
    return normalizeLive(response.data, 'trips');
  },
  getDashboard: async (): Promise<TransportDashboardData> => {
    const response = await api.get('/road/dashboard');
    return normalizeDashboard(response.data);
  },
  control: async (action: string, speed?: number) => {
    const response = await api.post('/road/sim/control', { action, speed });
    return response.data;
  },
};

export const seaAPI = {
  getLive: async (): Promise<TransportLiveData> => {
    const response = await api.get('/sea/live');
    return normalizeLive(response.data, 'vessels');
  },
  getDashboard: async (): Promise<TransportDashboardData> => {
    const response = await api.get('/sea/dashboard');
    return normalizeDashboard(response.data);
  },
  control: async (action: string, speed?: number) => {
    const response = await api.post('/sea/sim/control', { action, speed });
    return response.data;
  },
};

export default api;
