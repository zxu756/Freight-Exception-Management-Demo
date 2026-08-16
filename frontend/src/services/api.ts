// API client for backend communication
import axios from 'axios';
import type { TransportLiveData, TransportDashboardData } from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Live transport simulator API (air / road / sea / rail)
const normalizeLive = (data: any, tasksKey: string): TransportLiveData => ({
  simulator: data.simulator,
  tasks_total: data[tasksKey]?.total_in_db ?? 0,
  by_status: data[tasksKey]?.by_status ?? {},
  open_exceptions: data.open_exceptions ?? [],
  recent_events: data.recent_events ?? [],
  upcoming_departures: data.upcoming_departures ?? [],
  delayed_services: data.delayed_services ?? [],
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
  getEnvEvents: async () => {
    const response = await api.get('/air/env/events');
    return response.data;
  },
  triggerEnvEvent: async (body: Record<string, unknown>) => {
    const response = await api.post('/air/env/event', body);
    return response.data;
  },
  getException: async (exceptionId: string) => {
    const response = await api.get(`/air/exceptions/${exceptionId}`);
    return response.data;
  },
  getLines: async (ref: string) => {
    const response = await api.get(`/air/waybills/${ref}/house-bills`);
    return response.data;
  },
  decideException: async (exceptionId: string, body: Record<string, unknown>) => {
    const response = await api.post(`/air/exceptions/${exceptionId}/decision`, body);
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
  getSegments: async () => {
    const response = await api.get('/road/segments');
    return response.data;
  },
  getEnvEvents: async () => {
    const response = await api.get('/road/env/events');
    return response.data;
  },
  triggerEnvEvent: async (body: Record<string, unknown>) => {
    const response = await api.post('/road/env/event', body);
    return response.data;
  },
  getException: async (exceptionId: string) => {
    const response = await api.get(`/road/exceptions/${exceptionId}`);
    return response.data;
  },
  getLines: async (ref: string) => {
    const response = await api.get(`/road/consignments/${ref}/lines`);
    return response.data;
  },
  decideException: async (exceptionId: string, body: Record<string, unknown>) => {
    const response = await api.post(`/road/exceptions/${exceptionId}/decision`, body);
    return response.data;
  },
  control: async (action: string, speed?: number) => {
    const response = await api.post('/road/sim/control', { action, speed });
    return response.data;
  },
};

export const railAPI = {
  getLive: async (): Promise<TransportLiveData> => {
    const response = await api.get('/rail/live');
    return normalizeLive(response.data, 'services');
  },
  getDashboard: async (): Promise<TransportDashboardData> => {
    const response = await api.get('/rail/dashboard');
    return normalizeDashboard(response.data);
  },
  getKpi: async () => {
    const response = await api.get('/rail/kpi');
    return response.data;
  },
  getSegments: async () => {
    const response = await api.get('/rail/segments');
    return response.data;
  },
  getEnvEvents: async () => {
    const response = await api.get('/rail/env/events');
    return response.data;
  },
  triggerEnvEvent: async (body: Record<string, unknown>) => {
    const response = await api.post('/rail/env/event', body);
    return response.data;
  },
  getException: async (exceptionId: string) => {
    const response = await api.get(`/rail/exceptions/${exceptionId}`);
    return response.data;
  },
  getLines: async (ref: string) => {
    const response = await api.get(`/rail/consignments/${ref}/lines`);
    return response.data;
  },
  decideException: async (exceptionId: string, body: Record<string, unknown>) => {
    const response = await api.post(`/rail/exceptions/${exceptionId}/decision`, body);
    return response.data;
  },
  control: async (action: string, speed?: number) => {
    const response = await api.post('/rail/sim/control', { action, speed });
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
  getEnvEvents: async () => {
    const response = await api.get('/sea/env/events');
    return response.data;
  },
  triggerEnvEvent: async (body: Record<string, unknown>) => {
    const response = await api.post('/sea/env/event', body);
    return response.data;
  },
  getException: async (exceptionId: string) => {
    const response = await api.get(`/sea/exceptions/${exceptionId}`);
    return response.data;
  },
  getLines: async (ref: string) => {
    const response = await api.get(`/sea/containers/${ref}/lines`);
    return response.data;
  },
  decideException: async (exceptionId: string, body: Record<string, unknown>) => {
    const response = await api.post(`/sea/exceptions/${exceptionId}/decision`, body);
    return response.data;
  },
  control: async (action: string, speed?: number) => {
    const response = await api.post('/sea/sim/control', { action, speed });
    return response.data;
  },
};

// ---- World (God Panel) API ----
export const worldAPI = {
  getClock: async () => (await api.get('/world/clock')).data,
  controlClock: async (body: Record<string, unknown>) => (await api.post('/world/clock/control', body)).data,
  getWeather: async () => (await api.get('/world/weather')).data,
  setWeatherOverride: async (body: Record<string, unknown>) => (await api.post('/world/weather/override', body)).data,
  clearWeather: async () => (await api.post('/world/weather/clear', {})).data,
  getState: async () => (await api.get('/world/state')).data,
  getShipments: async () => (await api.get('/world/shipments')).data,
  getPredictions: async () => (await api.get('/world/predictions')).data,
  getCustomers: async (q?: string) => (await api.get('/world/customers', { params: q ? { q } : undefined })).data,
  getCarrierPerformance: async (riskyOnly = true, limit = 20) => (await api.get('/world/carrier-performance', { params: { risky_only: riskyOnly, limit } })).data,
  getMetrics: async (hours = 72) => (await api.get('/world/metrics', { params: { hours } })).data,
  getTickets: async (limit = 100) => (await api.get('/world/tickets', { params: { limit } })).data,
  getCustomerContacts: async (limit = 50) => (await api.get('/world/customer-contacts', { params: { limit } })).data,
  recordCustomerContact: async (body: Record<string, unknown>) => (await api.post('/world/customer-contacts', body)).data,
  markNotificationDelivered: async (notificationId: string, body: Record<string, unknown>) => (await api.post(`/notifications/${notificationId}/delivery`, body)).data,
};

export default api;
