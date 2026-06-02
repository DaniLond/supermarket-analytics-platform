import { useCallback, useEffect, useRef, useState } from 'react'
import { segmentationApi } from '../services/apiClient'
import type { ClusterProfile, ScatterPoint } from '../types'

const CLUSTER_COLORS = [
  '#2563eb', '#dc2626', '#16a34a', '#9333ea',
  '#ea580c', '#0891b2', '#ca8a04', '#be185d',
]

function clusterColor(cluster: number): string {
  return CLUSTER_COLORS[cluster % CLUSTER_COLORS.length]
}

function fmt(n: number, decimals = 1): string {
  return n.toLocaleString('es-CO', { maximumFractionDigits: decimals })
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">{children}</h3>
}

function LoadingBox() {
  return <div className="h-64 w-full bg-gray-50 rounded-lg animate-pulse" />
}

// ---------------------------------------------------------------------------
// Scatter plot PCA (SVG custom)
// ---------------------------------------------------------------------------

function ScatterPlot({ points, profiles, loading }: {
  points: ScatterPoint[]
  profiles: ClusterProfile[]
  loading: boolean
}) {
  if (loading) return <LoadingBox />
  if (!points.length) return <p className="text-sm text-gray-400">Sin datos</p>

  const padL = 36, padR = 16, padT = 16, padB = 36
  const svgW = 680, svgH = 420
  const plotW = svgW - padL - padR
  const plotH = svgH - padT - padB

  const xs = points.map((p) => p.pca_x)
  const ys = points.map((p) => p.pca_y)
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)

  const scaleX = (v: number) => padL + ((v - minX) / (maxX - minX + 1e-9)) * plotW
  const scaleY = (v: number) => padT + ((maxY - v) / (maxY - minY + 1e-9)) * plotH

  const labelMap = Object.fromEntries(profiles.map((p) => [p.cluster_id, p.label]))

  const x0 = minX <= 0 && maxX >= 0 ? scaleX(0) : null
  const y0 = minY <= 0 && maxY >= 0 ? scaleY(0) : null

  const xTicks = [0, 1, 2, 3, 4].map((i) => minX + (i / 4) * (maxX - minX))
  const yTicks = [0, 1, 2, 3, 4].map((i) => maxY - (i / 4) * (maxY - minY))

  return (
    <div className="overflow-x-auto">
      <svg width={svgW} height={svgH} style={{ display: 'block' }}>
        {xTicks.map((t, i) => (
          <g key={i}>
            <line x1={scaleX(t)} x2={scaleX(t)} y1={padT} y2={padT + plotH} stroke="#f3f4f6" strokeWidth={1} />
            <text x={scaleX(t)} y={svgH - padB + 14} textAnchor="middle" fontSize={9} fill="#9ca3af">
              {t.toFixed(1)}
            </text>
          </g>
        ))}
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={padL} x2={padL + plotW} y1={scaleY(t)} y2={scaleY(t)} stroke="#f3f4f6" strokeWidth={1} />
            <text x={padL - 4} y={scaleY(t) + 4} textAnchor="end" fontSize={9} fill="#9ca3af">
              {t.toFixed(1)}
            </text>
          </g>
        ))}

        {x0 !== null && (
          <line x1={x0} x2={x0} y1={padT} y2={padT + plotH} stroke="#d1d5db" strokeWidth={1} strokeDasharray="4 2" />
        )}
        {y0 !== null && (
          <line x1={padL} x2={padL + plotW} y1={y0} y2={y0} stroke="#d1d5db" strokeWidth={1} strokeDasharray="4 2" />
        )}

        <rect x={padL} y={padT} width={plotW} height={plotH} fill="none" stroke="#e5e7eb" strokeWidth={1} />

        {points.map((p) => (
          <circle
            key={p.customer_id}
            cx={scaleX(p.pca_x)}
            cy={scaleY(p.pca_y)}
            r={3.5}
            fill={clusterColor(p.cluster)}
            opacity={0.75}
          >
            <title>{`Cliente ${p.customer_id} · ${labelMap[p.cluster] ?? `Clúster ${p.cluster}`}\nPC1: ${p.pca_x.toFixed(3)}  PC2: ${p.pca_y.toFixed(3)}`}</title>
          </circle>
        ))}

        <text x={padL + plotW / 2} y={svgH - 2} textAnchor="middle" fontSize={9} fill="#6b7280">
          Componente Principal 1
        </text>
        <text
          x={10}
          y={padT + plotH / 2}
          textAnchor="middle"
          fontSize={9}
          fill="#6b7280"
          transform={`rotate(-90, 10, ${padT + plotH / 2})`}
        >
          Componente Principal 2
        </text>
      </svg>

      <div className="flex flex-wrap gap-3 mt-3">
        {profiles.map((p) => (
          <div key={p.cluster_id} className="flex items-center gap-1.5 text-xs text-gray-600">
            <span
              className="inline-block w-3 h-3 rounded-full"
              style={{ backgroundColor: clusterColor(p.cluster_id) }}
            />
            <span className="font-medium">{p.label}</span>
            <span className="text-gray-400">({p.customer_count})</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tarjetas de perfil de clúster
// ---------------------------------------------------------------------------

function ClusterCards({ profiles, loading }: { profiles: ClusterProfile[]; loading: boolean }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-40 bg-gray-50 rounded-xl animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
      {profiles.map((p) => (
        <div key={p.cluster_id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <div className="flex items-center gap-2 mb-3">
            <span
              className="inline-block w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: clusterColor(p.cluster_id) }}
            />
            <span className="font-semibold text-gray-800 text-sm">{p.label}</span>
            <span className="ml-auto text-xs text-gray-400">{p.customer_count} clientes</span>
          </div>
          <div className="grid grid-cols-2 gap-y-2 text-xs">
            <span className="text-gray-500">Frecuencia prom.</span>
            <span className="font-medium text-right">{fmt(p.avg_frequency)} tx</span>
            <span className="text-gray-500">Categorías únicas</span>
            <span className="font-medium text-right">{fmt(p.avg_unique_categories)}</span>
            <span className="text-gray-500">Tamaño canasta</span>
            <span className="font-medium text-right">{fmt(p.avg_basket_size)}</span>
            <span className="text-gray-500">Días desde última compra</span>
            <span className="font-medium text-right">{fmt(p.avg_recency_days, 0)} días</span>
          </div>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Página principal
// ---------------------------------------------------------------------------

type Phase = 'checking' | 'training' | 'ready' | 'error'

interface SegStatus {
  ready: boolean
  training: boolean
  error: string | null
}

export default function AdvancedAnalysis() {
  const [phase, setPhase] = useState<Phase>('checking')
  const [trainError, setTrainError] = useState<string | null>(null)
  const [dataLoading, setDataLoading] = useState(false)
  const [profiles, setProfiles] = useState<ClusterProfile[]>([])
  const [scatter, setScatter] = useState<ScatterPoint[]>([])
  const dataLoadedRef = useRef(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadData = useCallback(async () => {
    if (dataLoadedRef.current) return
    dataLoadedRef.current = true
    setDataLoading(true)
    try {
      const [prof, scat] = await Promise.all([
        segmentationApi.clusters(),
        segmentationApi.scatter(),
      ])
      setProfiles(prof.clusters)
      setScatter(scat.points)
    } catch (e: unknown) {
      dataLoadedRef.current = false
      const err = e as { message?: string }
      setTrainError(err.message ?? 'Error cargando datos de segmentación')
      setPhase('error')
    } finally {
      setDataLoading(false)
    }
  }, [])

  useEffect(() => {
    async function checkStatus() {
      try {
        const s: SegStatus = await segmentationApi.status()

        if (s.ready) {
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
          setPhase('ready')
          loadData()
        } else if (s.error) {
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
          setTrainError(s.error)
          setPhase('error')
        } else {
          // training or pending
          setPhase('training')
          if (!intervalRef.current) {
            intervalRef.current = setInterval(checkStatus, 10_000)
          }
        }
      } catch {
        // network issue — keep polling
        if (!intervalRef.current) {
          intervalRef.current = setInterval(checkStatus, 10_000)
        }
      }
    }

    checkStatus()

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [loadData])

  return (
    <div className="max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Análisis Avanzado</h2>
      </div>

      {/* Estado: verificando */}
      {phase === 'checking' && (
        <div className="flex items-center gap-3 text-gray-500 text-sm py-12 justify-center">
          <span className="animate-spin text-lg">⟳</span>
          Verificando estado del modelo…
        </div>
      )}

      {/* Estado: entrenando */}
      {phase === 'training' && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-8 flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-blue-800 font-medium text-sm">Entrenando modelo K-Means con PySpark…</p>
          <p className="text-blue-600 text-xs text-center max-w-sm">
            El proceso analiza todos los clientes y encuentra los segmentos óptimos.
            Esto puede tardar varios minutos. La página se actualizará automáticamente.
          </p>
        </div>
      )}

      {/* Estado: error */}
      {phase === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6">
          <p className="text-red-800 font-medium text-sm mb-2">El entrenamiento falló</p>
          <pre className="text-red-700 text-xs bg-red-100 rounded p-3 overflow-auto max-h-48 whitespace-pre-wrap">
            {trainError}
          </pre>
          <p className="text-red-600 text-xs mt-3">
            Revisa los logs del backend con <code className="bg-red-100 px-1 rounded">docker compose logs backend</code> para ver el error completo de Spark.
          </p>
        </div>
      )}

      {/* Contenido principal */}
      {phase === 'ready' && (
        <>
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-6">
            <SectionTitle>Mapa de Clientes — Proyección PCA 2D</SectionTitle>
            <p className="text-xs text-gray-400 mb-4">
              Cada punto es un cliente. Los ejes son las dos componentes principales de{' '}
              <span className="font-medium">frecuencia, categorías únicas, tamaño de canasta y recencia</span>.
              El color indica el clúster K-Means asignado.
            </p>
            <ScatterPlot points={scatter} profiles={profiles} loading={dataLoading} />
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <SectionTitle>Perfiles de Clústeres</SectionTitle>
            <ClusterCards profiles={profiles} loading={dataLoading} />
          </div>
        </>
      )}
    </div>
  )
}