import axios from 'axios';

// API base URL - nginx proxies /api/ to backend:8000
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/users/token/refresh/`, {
            refresh: refreshToken,
          });
          
          const { access } = response.data;
          localStorage.setItem('access_token', access);
          
          originalRequest.headers.Authorization = `Bearer ${access}`;
          return api(originalRequest);
        }
        // eslint-disable-next-line @typescript-eslint/no-unused-vars 
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/';
      }
    }

    return Promise.reject(error);
  }
);

// Auth API functions
export const authAPI = {
  // Register new user
  register: async (data: { username: string; email: string; password: string }) => {
    const response = await api.post('/users/register/', data);
    return response.data;
  },

  // Login user
  login: async (data: { username: string; password: string }) => {
    const response = await api.post('/users/login/', data);
    const { access, refresh } = response.data;
    
    // Store tokens
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    
    return response.data;
  },

  // Get user profile
  getProfile: async () => {
    const response = await api.get('/users/profile/');
    return response.data;
  },

  // Update user profile
  updateProfile: async (data: Partial<{ email: string; preferred_subject: string }>) => {
    const response = await api.patch('/users/profile/', data);
    return response.data;
  },

  // Get leaderboard
  getLeaderboard: async () => {
    const response = await api.get('/users/leaderboard/');
    return response.data;
  },

  // Logout (clear tokens)
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};

// Game API functions
export const gameAPI = {
  // Create or join game
  createOrJoinGame: async (data: { code?: string; subjects?: string[]; is_vs_ai?: boolean; ai_difficulty?: string }) => {
    const response = await api.post('/core/game/', data);
    return response.data;
  },

  // Get game details
  getGame: async (code: string) => {
    const response = await api.get(`/core/game/${code}/`);
    return response.data;
  },

  // Get quiz question
  getQuizQuestion: async (subject: string = 'Math') => {
    const response = await api.get(`/core/quiz/?subject=${subject}`);
    return response.data;
  },

  // Submit quiz answer
  submitQuizAnswer: async (moveId: number, data: { question_id: number; answer: string }) => {
    const response = await api.post(`/core/move/${moveId}/quiz/`, data);
    return response.data;
  },

  // Get game analysis
  getGameAnalysis: async (code: string) => {
    const response = await api.get(`/core/game/${code}/analysis/`);
    return response.data;
  },

  // Get matchmaking status
  getMatchmakingStatus: async () => {
    const response = await api.get('/core/matchmaking/status/');
    return response.data;
  },
};

// Utility functions
export const isAuthenticated = (): boolean => {
  return !!localStorage.getItem('access_token');
};

export const getAuthToken = (): string | null => {
  return localStorage.getItem('access_token');
};

export default api; 