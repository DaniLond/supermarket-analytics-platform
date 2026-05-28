import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { summaryApi } from '../services/apiClient'
import type {
  CategoryShare,
  Filters,
  KpiResponse,
  PeakDayCell,
  TopCategoriesResponse,
  TopCustomersResponse,
} from '../types'


const DOW_LABELS: Record<number, string> = {
  0: 'Dom', 1: 'Lun', 2: 'Mar', 3: 'Mié', 4: 'Jue', 5: 'Vie', 6: 'Sáb',
}
const STORES = [102, 103, 107, 110]
const PIE_COLORS = [
  '#2563eb', '#7c3aed', '#db2777', '#ea580c', '#16a34a',
  '#0891b2', '#ca8a04', '#9333ea', '#dc2626', '#65a30d', '#94a3b8',
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt(n: number): string {
  return n.toLocaleString('es-CO')
}

function interpolateColor(t: number): string {
  // t in [0,1]: white → brand blue (#2563eb)
  const r = Math.round(255 + (37 - 255) * t)
  const g = Math.round(255 + (99 - 255) * t)
  const b = Math.round(255 + (235 - 255) * t)
  return `rgb(${r},${g},${b})`
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function KpiCard({ label, value, loading }: { label: string; value: number; loading: boolean }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex flex-col gap-1">
      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</span>
      {loading ? (
        <div className="h-8 w-24 bg-gray-100 rounded animate-pulse" />
      ) : (
        <span className="text-3xl font-bold text-brand-700">{fmt(value)}</span>
      )}
    </div>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">{children}</h3>
}

function LoadingBox() {
  return <div className="h-64 w-full bg-gray-50 rounded-lg animate-pulse" />
}

// ---------------------------------------------------------------------------
// Peak days heatmap
// ---------------------------------------------------------------------------

function PeakHeatmap({ cells, loading }: { cells: PeakDayCell[]; loading: boolean }) {
  if (loading) return <LoadingBox />

  const days = Array.from({ length: 31 }, (_, i) => i + 1)
  const dows = [1, 2, 3, 4, 5, 6, 0]
  const lookup: Record<number, Record<number, number>> = {}
  let maxCount = 0
  for (const cell of cells) {
    if (!lookup[cell.day_of_week]) lookup[cell.day_of_week] = {}
    lookup[cell.day_of_week][cell.day_of_month] = cell.transaction_count
    if (cell.transaction_count > maxCount) maxCount = cell.transaction_count
  }

  const cellW = 18
  const cellH = 18
  const gap = 2
  const labelW = 28
  const labelH = 18
  const svgW = labelW + days.length * (cellW + gap)
  const svgH = labelH + dows.length * (cellH + gap) + 4

  return (
    <div className="overflow-x-auto">
      <svg width={svgW} height={svgH} style={{ display: 'block' }}>
        {days.map((d) => (
          <text
            key={d}
            x={labelW + (d - 1) * (cellW + gap) + cellW / 2}
            y={labelH - 4}
            textAnchor="middle"
            fontSize={9}
            fill="#6b7280"
          >
            {d % 5 === 0 || d === 1 ? d : ''}
          </text>
        ))}

        {dows.map((dow, ri) => (
          <g key={dow}>
            <text
              x={labelW - 4}
              y={labelH + ri * (cellH + gap) + cellH / 2 + 4}
              textAnchor="end"
              fontSize={9}
              fill="#6b7280"
            >
              {DOW_LABELS[dow]}
            </text>
            {days.map((d) => {
              const count = lookup[dow]?.[d] ?? 0
              const t = maxCount > 0 ? count / maxCount : 0
              return (
                <rect
                  key={d}
                  x={labelW + (d - 1) * (cellW + gap)}
                  y={labelH + ri * (cellH + gap)}
                  width={cellW}
                  height={cellH}
                  rx={3}
                  fill={count === 0 ? '#f3f4f6' : interpolateColor(t)}
                >
                  <title>{`${DOW_LABELS[dow]} día ${d}: ${fmt(count)} transacciones`}</title>
                </rect>
              )
            })}
          </g>
        ))}
      </svg>
      <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
        <span>Menos</span>
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <div
            key={t}
            className="w-4 h-4 rounded"
            style={{ backgroundColor: interpolateColor(t) }}
          />
        ))}
        <span>Más</span>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Category share pie
// ---------------------------------------------------------------------------

function SharePie({ shares, loading }: { shares: CategoryShare[]; loading: boolean }) {
  if (loading) return <LoadingBox />

  const TOP = 10
  const top = shares.slice(0, TOP)
  const rest = shares.slice(TOP)
  const otrosPct = rest.reduce((s, x) => s + x.share_pct, 0)
  const data = [
    ...top.map((x) => ({ name: x.category_name, value: x.share_pct })),
    ...(otrosPct > 0 ? [{ name: 'Otros', value: Math.round(otrosPct * 100) / 100 }] : []),
  ]

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="45%"
          outerRadius={90}
          dataKey="value"
          label={({ name, value }) => `${name} ${value}%`}
          labelLine={false}
          fontSize={10}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(v: number) => [`${v}%`, 'Participación']} />
      </PieChart>
    </ResponsiveContainer>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ExecutiveSummary() {
  const [filters, setFilters] = useState<Filters>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [kpiUnits, setKpiUnits] = useState<KpiResponse | null>(null)
  const [kpiTx, setKpiTx] = useState<KpiResponse | null>(null)
  const [kpiCustomers, setKpiCustomers] = useState<KpiResponse | null>(null)
  const [topCats, setTopCats] = useState<TopCategoriesResponse | null>(null)
  const [topCusts, setTopCusts] = useState<TopCustomersResponse | null>(null)
  const [peakCells, setPeakCells] = useState<PeakDayCell[]>([])
  const [shares, setShares] = useState<CategoryShare[]>([])

  const fetchAll = useCallback(async (f: Filters) => {
    setLoading(true)
    setError(null)
    try {
      const [units, tx, custs, cats, cust10, peak, share] = await Promise.all([
        summaryApi.totalUnits(f),
        summaryApi.transactionCount(f),
        summaryApi.uniqueCustomers(f),
        summaryApi.topCategories(10, f),
        summaryApi.topCustomers(10, f),
        summaryApi.peakDays(f),
        summaryApi.categoryShare(f),
      ])
      setKpiUnits(units)
      setKpiTx(tx)
      setKpiCustomers(custs)
      setTopCats(cats)
      setTopCusts(cust10)
      setPeakCells(peak.cells)
      setShares(share.shares)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error cargando datos')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll(filters) }, [fetchAll, filters])

  function handleStore(e: React.ChangeEvent<HTMLSelectElement>) {
    const v = e.target.value
    setFilters((f) => ({ ...f, storeId: v === '' ? undefined : Number(v) }))
  }

  function handleDate(field: 'startDate' | 'endDate') {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      const v = e.target.value
      setFilters((f) => ({ ...f, [field]: v === '' ? undefined : v }))
    }
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Resumen Ejecutivo</h2>
        {error && (
          <span className="text-sm text-red-600 bg-red-50 px-3 py-1 rounded-full">{error}</span>
        )}
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-3 mb-6 bg-white p-4 rounded-xl shadow-sm border border-gray-100">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">Tienda</label>
          <select
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            onChange={handleStore}
            defaultValue=""
          >
            <option value="">Todas</option>
            {STORES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">Desde</label>
          <input
            type="date"
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            min="2013-01-01"
            max="2013-06-30"
            onChange={handleDate('startDate')}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">Hasta</label>
          <input
            type="date"
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            min="2013-01-01"
            max="2013-06-30"
            onChange={handleDate('endDate')}
          />
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <KpiCard
          label="Total de ventas"
          value={kpiUnits?.value ?? 0}
          loading={loading}
        />
        <KpiCard
          label="Transacciones únicas"
          value={kpiTx?.value ?? 0}
          loading={loading}
        />
        <KpiCard
          label="Clientes únicos"
          value={kpiCustomers?.value ?? 0}
          loading={loading}
        />
      </div>

      {/* Charts grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        {/* Top categorías por volumen */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <SectionTitle>Top 10 Categorías — Volumen</SectionTitle>
          {loading || !topCats ? (
            <LoadingBox />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={topCats.by_volume.map((c) => ({
                  name: c.category_name,
                  Volumen: c.volume,
                  Frecuencia: c.frequency,
                }))}
                layout="vertical"
                margin={{ left: 8, right: 16, top: 4, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={fmt} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={110} />
                <Tooltip formatter={(v: number) => fmt(v)} />
                <Bar dataKey="Volumen" fill="#2563eb" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top clientes por transacciones */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <SectionTitle>Top 10 Clientes — Transacciones</SectionTitle>
          {loading || !topCusts ? (
            <LoadingBox />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={topCusts.by_transactions.map((c) => ({
                  name: `#${c.customer_id}`,
                  Transacciones: c.transaction_count,
                  Categorías: c.unique_categories,
                }))}
                layout="vertical"
                margin={{ left: 8, right: 16, top: 4, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={fmt} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={56} />
                <Tooltip formatter={(v: number) => fmt(v)} />
                <Bar dataKey="Transacciones" fill="#7c3aed" radius={[0, 4, 4, 0]} />
                <Bar dataKey="Categorías" fill="#c4b5fd" radius={[0, 4, 4, 0]} />
                <Legend />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Participación por categoría */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <SectionTitle>Participación por Categoría (Top 10)</SectionTitle>
          <SharePie shares={shares} loading={loading} />
        </div>

        {/* Heatmap días pico */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <SectionTitle>Días Pico — Transacciones por Día de Semana × Día del Mes</SectionTitle>
          <PeakHeatmap cells={peakCells} loading={loading} />
        </div>

      </div>
    </div>
  )
}