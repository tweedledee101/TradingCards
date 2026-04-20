import axios from 'axios';
import { getAccessToken, clearTokens } from '../auth/tokenStorage';

/** Production default: API on api subdomain (TLS). Override with VITE_API_URL at build time. */
function resolveApiBaseUrl() {
  const fromEnv = import.meta.env.VITE_API_URL;
  if (fromEnv) return fromEnv;
  if (import.meta.env.DEV) return 'http://localhost:8000';
  return 'https://api.ragnarokgamez.com';
}

const API_BASE_URL = resolveApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const t = getAccessToken();
  if (t) {
    config.headers.Authorization = `Bearer ${t}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      clearTokens();
      const path = typeof window !== 'undefined' ? window.location.pathname : '';
      if (path && !path.startsWith('/auth/callback')) {
        window.location.assign('/');
      }
    }
    return Promise.reject(err);
  }
);

// Opportunities
export const getOpportunities = async (params = {}) => {
  const response = await api.get('/api/opportunities', { params });
  return response.data;
};

export const getAuctions = async (params = {}) => {
  const response = await api.get('/api/auctions', { params });
  return response.data;
};

export const getMarketplaceOpportunities = async (params = {}) => {
  const response = await api.get('/api/marketplace', { params });
  return response.data;
};

export const getOpportunityStats = async () => {
  const response = await api.get('/api/opportunities-stats');
  return response.data;
};

/** Business pace + market listing pulse for Opportunities page */
export const getOpportunitiesContextStrip = async () => {
  const response = await api.get('/api/opportunities/context-strip');
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

/** PSA population data; 404 if none — use try/catch in caller */
export const getGradingForCard = async (id) => {
  const response = await api.get(`/api/grading/${id}`);
  return response.data;
};

/** External price benchmarks; 404 if none — use try/catch in caller */
export const getPriceBenchmarksForCard = async (id) => {
  const response = await api.get(`/api/benchmarks/${id}`);
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

/** UTF-8 CSV: purchase_date, purchase_price, card_id | player_name+card_year[+set+#] */
export const bulkImportInventory = async (file) => {
  const form = new FormData();
  form.append('file', file);
  const response = await api.post('/api/inventory/bulk-import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
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

// Business Operating System
export const getBusinessDashboard = async () => {
  const response = await api.get('/api/business/dashboard');
  return response.data;
};

export const getBusinessTrajectory = async () => {
  const response = await api.get('/api/business/trajectory');
  return response.data;
};

export const getBusinessPlan = async (hours = null) => {
  const params = hours ? { hours } : {};
  const response = await api.get('/api/business/plan/today', { params });
  return response.data;
};

export const setBusinessGoal = async (data) => {
  const response = await api.post('/api/business/goals', data);
  return response.data;
};

export const recordCapitalTransaction = async (data) => {
  const response = await api.post('/api/business/capital', data);
  return response.data;
};

export const getBusinessHistory = async (days = 30) => {
  const response = await api.get('/api/business/history', { params: { days } });
  return response.data;
};

export default api;
