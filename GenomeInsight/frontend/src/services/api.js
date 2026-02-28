import axios from "axios";

const API_BASE = process.env.REACT_APP_API_URL || "/api/v1";

const api = axios.create({ baseURL: API_BASE });

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401, try to refresh; if that fails, force logout
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (
      error.response?.status === 401 &&
      !original._retry &&
      !original.url?.includes("/auth/")
    ) {
      original._retry = true;
      const refresh = localStorage.getItem("refresh_token");
      if (refresh) {
        try {
          const { data } = await axios.post(`${API_BASE}/auth/refresh`, null, {
            headers: { Authorization: `Bearer ${refresh}` },
          });
          localStorage.setItem("access_token", data.access_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        } catch {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────

export const authAPI = {
  register: (email, password) =>
    api.post("/auth/register", { email, password, tos_accepted: true }),
  login: (email, password) => api.post("/auth/login", { email, password }),
  refresh: () => {
    const token = localStorage.getItem("refresh_token");
    return axios.post(`${API_BASE}/auth/refresh`, null, {
      headers: { Authorization: `Bearer ${token}` },
    });
  },
  logout: () => api.post("/auth/logout"),
};

// ── Genome ────────────────────────────────────────────────────────────────

export const genomeAPI = {
  upload: (file, sourceService, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    form.append("source_service", sourceService || "other");
    return api.post("/genome/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: onProgress,
    });
  },
  listUploads: () => api.get("/genome/uploads"),
  getUpload: (id) => api.get(`/genome/uploads/${id}`),
  deleteUpload: (id) => api.delete(`/genome/uploads/${id}`),
  getAnalysis: (id) => api.get(`/genome/analysis/${id}`),
  getReport: (id) => api.get(`/genome/analysis/${id}/report`),
  getRecommendations: (id) => api.get(`/genome/analysis/${id}/recommendations`),
  getVariants: (id, params) => api.get(`/genome/analysis/${id}/variants`, { params }),
  getRisks: (id) => api.get(`/genome/analysis/${id}/risks`),
  triggerAnalysis: (uploadId) => api.post(`/genome/uploads/${uploadId}/analyze`),
};

// ── Blood ─────────────────────────────────────────────────────────────────

export const bloodAPI = {
  upload: (file, testDate, labName, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    form.append("test_date", testDate);
    if (labName) form.append("lab_name", labName);
    return api.post("/blood/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: onProgress,
    });
  },
  listUploads: () => api.get("/blood/uploads"),
  getUpload: (id) => api.get(`/blood/uploads/${id}`),
  deleteUpload: (id) => api.delete(`/blood/uploads/${id}`),
  updateResults: (id, results) =>
    api.put(`/blood/uploads/${id}/results`, { results }),
  getHistory: () => api.get("/blood/history"),
  analyzeChanges: (currentId, previousId) =>
    api.post("/blood/analyze-changes", {
      current_upload_id: currentId || undefined,
      previous_upload_id: previousId || undefined,
    }),
  getTrends: (markers, fromDate, toDate) =>
    api.get("/blood/trends", {
      params: {
        markers: markers?.join(","),
        from_date: fromDate,
        to_date: toDate,
      },
    }),
  listMarkers: () => api.get("/blood/markers"),
};

// ── Epigenetics ──────────────────────────────────────────────────────────

export const epigeneticsAPI = {
  upload: (file, dataType, assayType, tissueType, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    form.append("data_type", dataType);
    if (assayType) form.append("assay_type", assayType);
    if (tissueType) form.append("tissue_type", tissueType);
    return api.post("/epigenetics/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: onProgress,
    });
  },
  listUploads: () => api.get("/epigenetics/uploads"),
  getUpload: (id) => api.get(`/epigenetics/uploads/${id}`),
  deleteUpload: (id) => api.delete(`/epigenetics/uploads/${id}`),
  getAnalysis: (id) => api.get(`/epigenetics/analysis/${id}`),
  getRegions: (id, params) =>
    api.get(`/epigenetics/analysis/${id}/regions`, { params }),
  getGenomeOverlay: (id) =>
    api.get(`/epigenetics/analysis/${id}/genome-overlay`),
  triggerAnalysis: (uploadId) =>
    api.post(`/epigenetics/uploads/${uploadId}/analyze`),
};

// ── Wearables ────────────────────────────────────────────────────────────

export const wearablesAPI = {
  listProviders: () => api.get("/wearables/providers"),
  connect: (provider) => api.post("/wearables/connect", { provider }),
  callback: (code, provider) =>
    api.post("/wearables/callback", { code, provider }),
  listConnections: () => api.get("/wearables/connections"),
  disconnect: (id) => api.delete(`/wearables/connections/${id}`),
  triggerSync: (id) => api.post(`/wearables/connections/${id}/sync`),
  getData: (params) => api.get("/wearables/data", { params }),
  getLatestData: () => api.get("/wearables/data/latest"),
};

// ── Microbiome ───────────────────────────────────────────────────────────

export const microbiomeAPI = {
  upload: (file, sampleType, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    if (sampleType) form.append("sample_type", sampleType);
    return api.post("/microbiome/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: onProgress,
    });
  },
  listUploads: () => api.get("/microbiome/uploads"),
  getUpload: (id) => api.get(`/microbiome/uploads/${id}`),
  deleteUpload: (id) => api.delete(`/microbiome/uploads/${id}`),
  getAnalysis: (id) => api.get(`/microbiome/analysis/${id}`),
  getTaxa: (id, params) =>
    api.get(`/microbiome/analysis/${id}/taxa`, { params }),
  getComposition: (id) =>
    api.get(`/microbiome/analysis/${id}/composition`),
  getGenomeCorrelation: (id) =>
    api.get(`/microbiome/analysis/${id}/genome-correlation`),
  triggerAnalysis: (uploadId) =>
    api.post(`/microbiome/uploads/${uploadId}/analyze`),
  getFullAnalysis: (id) => api.get(`/microbiome/analysis/${id}/full`),
};

// ── Insights ─────────────────────────────────────────────────────────────

export const insightsAPI = {
  getDaily: () => api.get("/insights/daily"),
  getHistory: (params) => api.get("/insights/history", { params }),
  generate: () => api.post("/insights/generate"),
};

// ── Unified Analysis ─────────────────────────────────────────────────────

export const analysisAPI = {
  getDaily: () => api.get("/analysis/daily"),
  triggerGenerate: () => api.post("/analysis/daily/generate"),
};

export default api;
