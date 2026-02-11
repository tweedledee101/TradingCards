import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Trending
export const getTrendingCards = async (limit = 25, filters = {}) => {
  const params = new URLSearchParams({ limit, ...filters });
  const response = await api.get(`/api/trending?${params}`);
  return response.data;
};

export const getMarketStats = async () => {
  const response = await api.get('/api/stats');
  return response.data;
};

// Cards
export const getCard = async (id, days = 30) => {
  const response = await api.get(`/api/cards/${id}?days=${days}`);
  return response.data;
};

export const searchCards = async (params) => {
  const response = await api.get('/api/cards', { params });
  return response.data;
};

// Inventory
export const getInventory = async (status = 'owned') => {
  const response = await api.get(`/api/inventory?status=${status}`);
  return response.data;
};

export const getInventoryStats = async () => {
  const response = await api.get('/api/inventory/stats');
  return response.data;
};

export const addToInventory = async (data) => {
  const response = await api.post('/api/inventory', data);
  return response.data;
};

export const recordSale = async (data) => {
  const response = await api.post('/api/inventory/sales', data);
  return response.data;
};

// Watchlist
export const getWatchlist = async () => {
  const response = await api.get('/api/watchlist');
  return response.data;
};

export const addToWatchlist = async (data) => {
  const response = await api.post('/api/watchlist', data);
  return response.data;
};

export const removeFromWatchlist = async (id) => {
  const response = await api.delete(`/api/watchlist/${id}`);
  return response.data;
};

export const getWatchlistAlerts = async () => {
  const response = await api.get('/api/watchlist/alerts');
  return response.data;
};

export default api;
