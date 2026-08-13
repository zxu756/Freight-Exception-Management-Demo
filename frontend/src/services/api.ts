// API client for backend communication
import axios from 'axios';
import type { TransportLiveData, TransportDashboardData } from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

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
  getKpi: async () => {
    const response = await api.get('/air/kpi');
    return response.data;
  },
  getException: async (exceptionId: string) => {
    const response = await api.get(`/air/exceptions/${exceptionId}`);
    return response.data;
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
  getKpi: async () => {
    const response = await api.get('/road/kpi');
    return response.data;
  },
  getException: async (exceptionId: string) => {
    const response = await api.get(`/road/exceptions/${exceptionId}`);
    return response.data;
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
  getKpi: async () => {
    const response = await api.get('/sea/kpi');
    return response.data;
  },
  getException: async (exceptionId: string) => {
    const response = await api.get(`/sea/exceptions/${exceptionId}`);
    return response.data;
  },
  control: async (action: string, speed?: number) => {
    const response = await api.post('/sea/sim/control', { action, speed });
    return response.data;
  },
};

export default api;
