import { useCallback, useEffect, useState } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { analyticsApi } from '../services/apiClient'
import type {
  BoxplotResponse,
  BoxplotStats,
  CorrelationHeatmapResponse,
  Filters,
  TimeSeriesResponse,
} from '../types'

const STORES = [102, 103, 107, 110]

const FEATURE_LABELS: Record<string, string> = {
  frequency: 'Frecuencia',
  unique_categories: 'Categorías únicas',
  avg_basket_size: 'Tam. canasta',
}

const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

function fmt(n: number): string {
  return n.toLocaleString('es-CO')
}

function corrColor(r: number): string {
  const t = Math.abs(r)
  if (r >= 0) {
    return `rgb(${Math.round(255 + (37 - 255) * t)},${Math.round(255 + (99 - 255) * t)},${Math.round(255 + (235 - 255) * t)})`
  }
  return `rgb(${Math.round(255 + (220 - 255) * t)},${Math.round(255 + (38 - 255) * t)},${Math.round(255 + (38 - 255) * t)})`
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">{children}</h3>
  )
}

function LoadingBox() {
  return <div className="h-64 w-full bg-gray-50 rounded-lg animate-pulse" />
}

// ---------------------------------------------------------------------------
// Boxplot SVG
// ---------------------------------------------------------------------------

function BoxplotChart({ stats, loading }: { stats: BoxplotStats[]; loading: boolean }) {
  if (loading) return <LoadingBox />
  if (!stats.length) return <p className="text-sm text-gray-400">Sin datos</p>

  const labelW = 132
  const rightPad = 24
  const rowH = 22
  const gap = 6
  const axisH = 20
  const footH = 20
  const plotW = 500
  const svgW = labelW + plotW + rightPad
  const svgH = axisH + stats.length * (rowH + gap) + footH

  const allVals = stats.flatMap((s) => [s.min, s.max, ...s.outliers])
  const maxVal = Math.max(...allVals, 1)
  const scale = (v: number) => (v / maxVal) * plotW

  const ticks = [0, 1, 2, 3, 4].map((i) => Math.round((maxVal * i) / 4))

  return (
    <div className="overflow-x-auto">
      <svg width={svgW} height={svgH} style={{ display: 'block' }}>
        {/* Grid lines + axis ticks */}
        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={labelW + scale(t)} x2={labelW + scale(t)}
              y1={axisH - 4} y2={svgH - footH}
              stroke="#e5e7eb" strokeWidth={1}
            />
            <text x={labelW + scale(t)} y={axisH - 6} textAnchor="middle" fontSize={9} fill="#9ca3af">
              {t}
            </text>
          </g>
        ))}

        {/* Rows */}
        {stats.map((s, i) => {
          const y = axisH + i * (rowH + gap)
          const midY = y + rowH / 2
          const boxY = y + 4
          const boxH = rowH - 8
          const tooltip = `${s.label} — Mín:${s.min} Q1:${s.q1} Med:${s.median} Q3:${s.q3} Máx:${s.max}`

          return (
            <g key={s.label}>
              <text x={labelW - 6} y={midY + 4} textAnchor="end" fontSize={9} fill="#374151">
                {s.label.length > 18 ? s.label.slice(0, 17) + '…' : s.label}
              </text>

              {/* Left whisker */}
              <line x1={labelW + scale(s.min)} x2={labelW + scale(s.q1)} y1={midY} y2={midY} stroke="#9ca3af" strokeWidth={1.5} />
              <line x1={labelW + scale(s.min)} x2={labelW + scale(s.min)} y1={midY - 4} y2={midY + 4} stroke="#9ca3af" strokeWidth={1.5} />

              {/* IQR box */}
              <rect
                x={labelW + scale(s.q1)} y={boxY}
                width={Math.max(scale(s.q3) - scale(s.q1), 1)} height={boxH}
                fill="#bfdbfe" stroke="#2563eb" strokeWidth={1.5} rx={2}
              >
                <title>{tooltip}</title>
              </rect>

              {/* Median */}
              <line x1={labelW + scale(s.median)} x2={labelW + scale(s.median)} y1={boxY} y2={boxY + boxH} stroke="#1d4ed8" strokeWidth={2} />

              {/* Right whisker */}
              <line x1={labelW + scale(s.q3)} x2={labelW + scale(s.max)} y1={midY} y2={midY} stroke="#9ca3af" strokeWidth={1.5} />
              <line x1={labelW + scale(s.max)} x2={labelW + scale(s.max)} y1={midY - 4} y2={midY + 4} stroke="#9ca3af" strokeWidth={1.5} />

              {/* Outliers */}
              {s.outliers.map((o, oi) => (
                <circle key={oi} cx={labelW + scale(o)} cy={midY} r={3} fill="none" stroke="#ef4444" strokeWidth={1.5} />
              ))}
            </g>
          )
        })}

        {/* X axis label */}
        <text x={labelW + plotW / 2} y={svgH - 4} textAnchor="middle" fontSize={9} fill="#9ca3af">
          Tamaño de canasta (# categorías distintas por transacción)
        </text>
      </svg>

      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded bg-blue-200 border border-blue-500" />
          IQR (Q1–Q3)
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-0.5 h-3 bg-blue-700" />
          Mediana
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-full border border-red-500" />
          Atípico
        </span>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Correlation heatmap SVG
// ---------------------------------------------------------------------------

function CorrHeatmap({ data, loading }: { data: CorrelationHeatmapResponse | null; loading: boolean }) {
  if (loading) return <LoadingBox />
  if (!data) return null

  const { features, cells } = data
  const cellSize = 72
  const labelH = 68
  const labelW = 112
  const svgW = labelW + features.length * cellSize + 4
  const svgH = labelH + features.length * cellSize + 4

  return (
    <div className="overflow-x-auto">
      <svg width={svgW} height={svgH} style={{ display: 'block' }}>
        {/* Column headers */}
        {features.map((f, ci) => (
          <text
            key={f}
            x={labelW + ci * cellSize + cellSize / 2}
            y={labelH - 6}
            textAnchor="end"
            fontSize={9}
            fill="#374151"
            transform={`rotate(-35, ${labelW + ci * cellSize + cellSize / 2}, ${labelH - 6})`}
          >
            {FEATURE_LABELS[f] ?? f}
          </text>
        ))}

        {/* Rows */}
        {features.map((fy, ri) => (
          <g key={fy}>
            <text x={labelW - 6} y={labelH + ri * cellSize + cellSize / 2 + 4} textAnchor="end" fontSize={9} fill="#374151">
              {FEATURE_LABELS[fy] ?? fy}
            </text>
            {features.map((fx, ci) => {
              const cell = cells.find((c) => c.feature_x === fx && c.feature_y === fy)
              const r = cell?.correlation ?? 0
              return (
                <g key={fx}>
                  <rect
                    x={labelW + ci * cellSize} y={labelH + ri * cellSize}
                    width={cellSize - 2} height={cellSize - 2}
                    fill={corrColor(r)} rx={4}
                  >
                    <title>{`${FEATURE_LABELS[fx] ?? fx} × ${FEATURE_LABELS[fy] ?? fy}: ${r.toFixed(3)}`}</title>
                  </rect>
                  <text
                    x={labelW + ci * cellSize + (cellSize - 2) / 2}
                    y={labelH + ri * cellSize + (cellSize - 2) / 2 + 4}
                    textAnchor="middle" fontSize={11} fontWeight="500"
                    fill={Math.abs(r) > 0.5 ? '#fff' : '#374151'}
                  >
                    {r.toFixed(2)}
                  </text>
                </g>
              )
            })}
          </g>
        ))}
      </svg>

      <div className="flex items-center gap-2 mt-3 text-xs text-gray-500">
        <div className="w-3 h-3 rounded" style={{ backgroundColor: corrColor(-1) }} />
        <span>−1</span>
        <div className="w-3 h-3 rounded bg-white border border-gray-200" />
        <span>0</span>
        <div className="w-3 h-3 rounded" style={{ backgroundColor: corrColor(1) }} />
        <span>+1</span>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

type Granularity = 'day' | 'week' | 'month'
type Dimension = 'category' | 'customer'

export default function AnalyticsExploration() {
  const [filters, setFilters] = useState<Filters>({})
  const [granularity, setGranularity] = useState<Granularity>('week')
  const [dimension, setDimension] = useState<Dimension>('category')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [timeSeries, setTimeSeries] = useState<TimeSeriesResponse | null>(null)
  const [boxplotData, setBoxplotData] = useState<BoxplotResponse | null>(null)
  const [corrData, setCorrData] = useState<CorrelationHeatmapResponse | null>(null)

  const fetchAll = useCallback(
    async (f: Filters, gran: Granularity, dim: Dimension) => {
      setLoading(true)
      setError(null)
      try {
        const [ts, bp, corr] = await Promise.all([
          analyticsApi.timeSeries(gran, f),
          analyticsApi.boxplot(dim, f),
          analyticsApi.correlationHeatmap(),
        ])
        setTimeSeries(ts)
        setBoxplotData(bp)
        setCorrData(corr)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Error cargando datos')
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  useEffect(() => { fetchAll(filters, granularity, dimension) }, [fetchAll, filters, granularity, dimension])

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

  const tickInterval = granularity === 'day' ? 14 : granularity === 'week' ? 3 : 0
  const tickFormatter = (v: string) => {
    const d = new Date(v + 'T12:00:00')
    if (granularity === 'month') return MONTHS[d.getMonth()]
    return `${d.getDate()}/${d.getMonth() + 1}`
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Visualizaciones Analíticas</h2>
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
            min="2013-01-01" max="2013-06-30"
            onChange={handleDate('startDate')}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-500">Hasta</label>
          <input
            type="date"
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            min="2013-01-01" max="2013-06-30"
            onChange={handleDate('endDate')}
          />
        </div>
      </div>

      {/* Time series */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-6">
        <div className="flex items-center justify-between mb-3">
          <SectionTitle>Serie de Tiempo</SectionTitle>
          <div className="flex gap-1">
            {(['day', 'week', 'month'] as const).map((g) => (
              <button
                key={g}
                onClick={() => setGranularity(g)}
                className={`px-3 py-1 text-xs rounded-lg font-medium transition-colors ${
                  granularity === g
                    ? 'bg-brand-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {g === 'day' ? 'Día' : g === 'week' ? 'Semana' : 'Mes'}
              </button>
            ))}
          </div>
        </div>
        {loading || !timeSeries ? (
          <LoadingBox />
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={timeSeries.points} margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="period"
                tick={{ fontSize: 10 }}
                interval={tickInterval}
                tickFormatter={tickFormatter}
              />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={fmt} />
              <Tooltip
                formatter={(v: number, name: string) => [
                  fmt(v),
                  name === 'transactions' ? 'Transacciones' : 'Líneas de categoría',
                ]}
                labelFormatter={(l: string) => `Período: ${l}`}
              />
              <Legend
                formatter={(v) =>
                  v === 'transactions' ? 'Transacciones' : 'Líneas de categoría'
                }
              />
              <Line type="monotone" dataKey="transactions" stroke="#2563eb" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="category_lines" stroke="#7c3aed" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Boxplot + Correlation heatmap */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <div className="flex items-center justify-between mb-3">
            <SectionTitle>Distribución del Tamaño de Canasta</SectionTitle>
            <div className="flex gap-1">
              {(['category', 'customer'] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setDimension(d)}
                  className={`px-3 py-1 text-xs rounded-lg font-medium transition-colors ${
                    dimension === d
                      ? 'bg-brand-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {d === 'category' ? 'Por categoría' : 'Por cliente'}
                </button>
              ))}
            </div>
          </div>
          <BoxplotChart stats={boxplotData?.stats ?? []} loading={loading} />
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <SectionTitle>Correlación entre Métricas del Cliente</SectionTitle>
          <CorrHeatmap data={corrData} loading={loading} />
        </div>
      </div>
    </div>
  )
}