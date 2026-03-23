import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Opportunities
export const getOpportunities = async (params = {}) => {
  const response = await api.get('/api/opportunities', { params });
  return response.data;
};

export const getAuctions = async (params = {}) => {
  const response = await api.get('/api/auctions', { params });
  return response.data;
};

export const getOpportunityStats = async () => {
  const response = await api.get('/api/opportunities-stats');
  return response.data;
};

export const getPlayerStats = async (playerName) => {
  const response = await api.get(`/api/players/${encodeURIComponent(playerName)}/stats`);
  return response.data;
};

export const getPlayerPriceHistory = async (playerName, days = 90) => {
  const response = await api.get(`/api/players/${encodeURIComponent(playerName)}/price-history`, { params: { days } });
  return response.data;
};

export const getPlayerTiming = async (playerName) => {
  const response = await api.get(`/api/players/${encodeURIComponent(playerName)}/timing`);
  return response.data;
};

// Scheduled Bids
export const getScheduledBids = async () => {
  const response = await api.get('/api/scheduled-bids');
  return response.data;
};

export const createScheduledBid = async (data) => {
  const response = await api.post('/api/scheduled-bids', data);
  return response.data;
};

export const cancelScheduledBid = async (id) => {
  const response = await api.delete(`/api/scheduled-bids/${id}`);
  return response.data;
};

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
