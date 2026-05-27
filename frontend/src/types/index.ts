// ── Filtros globales ──────────────────────────────────────────────────────────
export interface Filters {
  startDate?: string
  endDate?: string
  storeId?: number
}

// ── KPIs ──────────────────────────────────────────────────────────────────────
export interface KpiResponse {
  value: number
  label: string
}

// ── Categorías ────────────────────────────────────────────────────────────────
export interface CategoryStat {
  category_id: number
  category_name: string
  volume: number
  frequency: number
}

export interface TopCategoriesResponse {
  by_volume: CategoryStat[]
  by_frequency: CategoryStat[]
}

// ── Clientes ──────────────────────────────────────────────────────────────────
export interface CustomerStat {
  customer_id: number
  transaction_count: number
  unique_categories: number
}

export interface TopCustomersResponse {
  by_transactions: CustomerStat[]
  by_diversity: CustomerStat[]
}

// ── Heatmap de días pico ──────────────────────────────────────────────────────
export interface PeakDayCell {
  day_of_week: number
  day_of_month: number
  transaction_count: number
}

// ── Share de categorías ───────────────────────────────────────────────────────
export interface CategoryShare {
  category_id: number
  category_name: string
  volume: number
  share_pct: number
}

// ── Series de tiempo ──────────────────────────────────────────────────────────
export interface TimeSeriesPoint {
  period: string
  transactions: number
  category_lines: number
}

// ── Boxplot ───────────────────────────────────────────────────────────────────
export interface BoxplotStats {
  label: string
  min: number
  q1: number
  median: number
  q3: number
  max: number
  outliers: number[]
}

// ── Segmentación ──────────────────────────────────────────────────────────────
export interface ClusterProfile {
  cluster_id: number
  customer_count: number
  avg_frequency: number
  avg_unique_categories: number
  avg_basket_size: number
  avg_recency_days: number
  label: string
}

export interface ScatterPoint {
  customer_id: number
  pca_x: number
  pca_y: number
  cluster: number
}

// ── Reglas de asociación ──────────────────────────────────────────────────────
export interface AssociationRule {
  antecedent: number[]
  consequent: number[]
  support: number
  confidence: number
  lift: number
}
