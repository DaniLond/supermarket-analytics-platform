import axios from 'axios'
import type { Filters } from '../types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
})

// Convierte los filtros opcionales en query params
function filtersToParams(filters?: Filters) {
  const params: Record<string, string | number> = {}
  if (filters?.startDate) params['start_date'] = filters.startDate
  if (filters?.endDate) params['end_date'] = filters.endDate
  if (filters?.storeId !== undefined) params['store_id'] = filters.storeId
  return params
}

// ── Summary ───────────────────────────────────────────────────────────────────
export const summaryApi = {
  totalUnits: (f?: Filters) =>
    api.get('/summary/total-units', { params: filtersToParams(f) }).then((r) => r.data),
  transactionCount: (f?: Filters) =>
    api.get('/summary/transaction-count', { params: filtersToParams(f) }).then((r) => r.data),
  uniqueCustomers: (f?: Filters) =>
    api.get('/summary/unique-customers', { params: filtersToParams(f) }).then((r) => r.data),
  topCategories: (limit = 10, f?: Filters) =>
    api
      .get('/summary/top-categories', { params: { limit, ...filtersToParams(f) } })
      .then((r) => r.data),
  topCustomers: (limit = 10, f?: Filters) =>
    api
      .get('/summary/top-customers', { params: { limit, ...filtersToParams(f) } })
      .then((r) => r.data),
  peakDays: (f?: Filters) =>
    api.get('/summary/peak-days', { params: filtersToParams(f) }).then((r) => r.data),
  categoryShare: (f?: Filters) =>
    api.get('/summary/category-share', { params: filtersToParams(f) }).then((r) => r.data),
}

// ── Analytics ─────────────────────────────────────────────────────────────────
export const analyticsApi = {
  timeSeries: (granularity: 'day' | 'week' | 'month' = 'day', f?: Filters) =>
    api
      .get('/analytics/time-series', { params: { granularity, ...filtersToParams(f) } })
      .then((r) => r.data),
  boxplot: (dimension: 'customer' | 'category' = 'category', f?: Filters) =>
    api
      .get('/analytics/boxplot', { params: { dimension, ...filtersToParams(f) } })
      .then((r) => r.data),
  correlationHeatmap: () => api.get('/analytics/correlation-heatmap').then((r) => r.data),
}

// ── Segmentation ──────────────────────────────────────────────────────────────
export const segmentationApi = {
  clusters: () => api.get('/segmentation/clusters').then((r) => r.data),
  customerCluster: (id: number) =>
    api.get(`/segmentation/customers/${id}/cluster`).then((r) => r.data),
  scatter: () => api.get('/segmentation/scatter').then((r) => r.data),
  retrain: () => api.post('/segmentation/retrain').then((r) => r.data),
}

// ── Recommendations ───────────────────────────────────────────────────────────
export const recommendationsApi = {
  byCategory: (id: number) =>
    api.get(`/recommendations/category/${id}`).then((r) => r.data),
  byCustomer: (id: number) =>
    api.get(`/recommendations/customer/${id}`).then((r) => r.data),
  productsByCategory: (id: number) =>
    api.get(`/recommendations/products-by-category/${id}`).then((r) => r.data),
}

// ── Transactions ──────────────────────────────────────────────────────────────
export const transactionsApi = {
  ingest: (transactions: object[]) =>
    api.post('/transactions', { transactions }).then((r) => r.data),
  retrain: () => api.post('/models/retrain').then((r) => r.data),
  modelStatus: () => api.get('/models/status').then((r) => r.data),
}

export default api
