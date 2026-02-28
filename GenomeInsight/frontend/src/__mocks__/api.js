// Mock for ../services/api
import { jest } from "@jest/globals";

export const authAPI = {
  login: jest.fn(),
  register: jest.fn(),
  refresh: jest.fn(),
  logout: jest.fn(),
};

export const genomeAPI = {
  upload: jest.fn(),
  listUploads: jest.fn(),
  getUpload: jest.fn(),
  deleteUpload: jest.fn(),
  getAnalysis: jest.fn(),
  getReport: jest.fn(),
  getRecommendations: jest.fn(),
  getVariants: jest.fn(),
  getRisks: jest.fn(),
  triggerAnalysis: jest.fn(),
};

export const bloodAPI = {
  upload: jest.fn(),
  listUploads: jest.fn(),
  getUpload: jest.fn(),
  deleteUpload: jest.fn(),
  updateResults: jest.fn(),
  getHistory: jest.fn(),
  analyzeChanges: jest.fn(),
  getTrends: jest.fn(),
  listMarkers: jest.fn(),
};

const api = { interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } } };
export default api;
