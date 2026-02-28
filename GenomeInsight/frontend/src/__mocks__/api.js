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

export const epigeneticsAPI = {
  upload: jest.fn(),
  listUploads: jest.fn(),
  getUpload: jest.fn(),
  deleteUpload: jest.fn(),
  getAnalysis: jest.fn(),
  getRegions: jest.fn(),
  getGenomeOverlay: jest.fn(),
  triggerAnalysis: jest.fn(),
};

export const microbiomeAPI = {
  upload: jest.fn(),
  listUploads: jest.fn(),
  getUpload: jest.fn(),
  deleteUpload: jest.fn(),
  getAnalysis: jest.fn(),
  getTaxa: jest.fn(),
  getComposition: jest.fn(),
  getGenomeCorrelation: jest.fn(),
  triggerAnalysis: jest.fn(),
  getFullAnalysis: jest.fn(),
};

export const wearablesAPI = {
  listProviders: jest.fn(),
  connect: jest.fn(),
  callback: jest.fn(),
  listConnections: jest.fn(),
  disconnect: jest.fn(),
  triggerSync: jest.fn(),
  getData: jest.fn(),
  getLatestData: jest.fn(),
};

export const insightsAPI = {
  getDaily: jest.fn(),
  getHistory: jest.fn(),
  generate: jest.fn(),
};

export const analysisAPI = {
  getDaily: jest.fn(),
  triggerGenerate: jest.fn(),
};

const api = { interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } } };
export default api;
