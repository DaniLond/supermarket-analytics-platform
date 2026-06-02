import { useCallback, useEffect, useRef, useState } from 'react'
import { transactionsApi } from '../services/apiClient'

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

interface PipelineStatus {
  transactions_loaded: boolean
  last_ingest_count: number
  last_ingest_error: string | null
  segmentation_training: boolean
  segmentation_error: string | null
  recommendations_training: boolean
  recommendations_error: string | null
  models_ready: boolean
}

// ---------------------------------------------------------------------------
// Indicador de estado (ok / running / error)
// ---------------------------------------------------------------------------

function StatusDot({ ok, running, error }: { ok: boolean; running: boolean; error?: string | null }) {
  if (running) return (
    <span className="flex items-center gap-1.5 text-blue-600 text-xs">
      <span className="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
      Entrenando…
    </span>
  )
  if (error) return (
    <span className="flex items-center gap-1.5 text-red-600 text-xs">
      <span className="inline-block w-2 h-2 rounded-full bg-red-500" />
      Error
    </span>
  )
  if (ok) return (
    <span className="flex items-center gap-1.5 text-green-600 text-xs">
      <span className="inline-block w-2 h-2 rounded-full bg-green-500" />
      Listo
    </span>
  )
  return (
    <span className="flex items-center gap-1.5 text-gray-400 text-xs">
      <span className="inline-block w-2 h-2 rounded-full bg-gray-300" />
      Pendiente
    </span>
  )
}

// ---------------------------------------------------------------------------
// Panel de estado del pipeline
// ---------------------------------------------------------------------------

function PipelinePanel({ status, onRetrain }: { status: PipelineStatus | null; onRetrain: () => void }) {
  const [retraining, setRetraining] = useState(false)

  const handleRetrain = async () => {
    setRetraining(true)
    try { await onRetrain() } finally { setRetraining(false) }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
        Estado del Pipeline
      </h3>

      {!status ? (
        <p className="text-sm text-gray-400">Cargando…</p>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2 border-b border-gray-50">
            <span className="text-sm text-gray-600">Datos de transacciones</span>
            <StatusDot ok={status.transactions_loaded} running={false} />
          </div>

          <div className="flex items-center justify-between py-2 border-b border-gray-50">
            <div>
              <span className="text-sm text-gray-600">Segmentación K-Means</span>
              {status.segmentation_error && (
                <p className="text-xs text-red-500 mt-0.5 max-w-xs truncate">{status.segmentation_error}</p>
              )}
            </div>
            <StatusDot
              ok={status.models_ready && !status.segmentation_training}
              running={status.segmentation_training}
              error={status.segmentation_error}
            />
          </div>

          <div className="flex items-center justify-between py-2 border-b border-gray-50">
            <div>
              <span className="text-sm text-gray-600">Recomendaciones FP-Growth</span>
              {status.recommendations_error && (
                <p className="text-xs text-red-500 mt-0.5 max-w-xs truncate">{status.recommendations_error}</p>
              )}
            </div>
            <StatusDot
              ok={status.models_ready && !status.recommendations_training}
              running={status.recommendations_training}
              error={status.recommendations_error}
            />
          </div>

          {status.last_ingest_count > 0 && (
            <p className="text-xs text-gray-500 pt-1">
              Última ingesta: <strong>{status.last_ingest_count}</strong> transacción(es) añadida(s)
            </p>
          )}

          <button
            onClick={handleRetrain}
            disabled={retraining || status.segmentation_training || status.recommendations_training}
            className="mt-2 w-full text-sm border border-gray-200 rounded-lg px-4 py-2 text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors"
          >
            {retraining ? 'Iniciando…' : 'Forzar re-entrenamiento de modelos'}
          </button>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Formulario de ingesta
// ---------------------------------------------------------------------------

const EXAMPLE = JSON.stringify(
  [
    { date: '2013-07-01', store_id: 102, customer_id: 9999, categories: [3, 7, 17] },
    { date: '2013-07-01', store_id: 103, customer_id: 8888, categories: [1, 6, 18, 25] },
  ],
  null,
  2
)

function IngestForm({ onSuccess }: { onSuccess: (count: number) => void }) {
  const [json, setJson] = useState(EXAMPLE)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null)

  const handleSubmit = async () => {
    let parsed: object[]
    try {
      parsed = JSON.parse(json)
      if (!Array.isArray(parsed)) throw new Error('Debe ser un array JSON')
    } catch (e: unknown) {
      const err = e as Error
      setResult({ ok: false, message: `JSON inválido: ${err.message}` })
      return
    }

    setLoading(true)
    setResult(null)
    try {
      const res = await transactionsApi.ingest(parsed)
      setResult({ ok: true, message: res.message })
      onSuccess(res.transactions_ingested)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setResult({ ok: false, message: err.response?.data?.detail ?? 'Error al ingestar.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-1">
        Añadir Nuevas Transacciones
      </h3>
      <p className="text-xs text-gray-500 mb-4">
        Pega un array JSON con las transacciones. Al enviar, se actualizan los datos y se
        re-entrenan los modelos automáticamente.
      </p>

      <div className="mb-3 text-xs text-gray-500 bg-gray-50 rounded-lg p-3 space-y-1">
        <p className="font-medium text-gray-600">Formato de cada transacción:</p>
        <p><code className="bg-white px-1 rounded border border-gray-200">date</code> — fecha en formato YYYY-MM-DD</p>
        <p><code className="bg-white px-1 rounded border border-gray-200">store_id</code> — ID de la tienda (102, 103, 107, 110)</p>
        <p><code className="bg-white px-1 rounded border border-gray-200">customer_id</code> — ID del cliente</p>
        <p><code className="bg-white px-1 rounded border border-gray-200">categories</code> — lista de IDs de categorías compradas</p>
      </div>

      <textarea
        value={json}
        onChange={(e) => setJson(e.target.value)}
        rows={12}
        className="w-full font-mono text-xs border border-gray-200 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-300 resize-y"
        spellCheck={false}
      />

      <button
        onClick={handleSubmit}
        disabled={loading}
        className="mt-3 bg-blue-600 text-white text-sm px-5 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {loading ? 'Enviando…' : 'Ingestar y re-entrenar'}
      </button>

      {result && (
        <div className={`mt-3 text-sm rounded-lg px-4 py-3 border ${
          result.ok
            ? 'bg-green-50 border-green-200 text-green-800'
            : 'bg-red-50 border-red-200 text-red-700'
        }`}>
          {result.message}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Página principal
// ---------------------------------------------------------------------------

export default function DataManagement() {
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      setStatus(await transactionsApi.pipelineStatus())
    } catch { /* red error — mantener estado anterior */ }
  }, [])

  // Polling cada 8s mientras algún modelo esté entrenando
  useEffect(() => {
    fetchStatus()
    intervalRef.current = setInterval(() => {
      fetchStatus()
    }, 8_000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [fetchStatus])

  const handleRetrain = async () => {
    await transactionsApi.retrain()
    await fetchStatus()
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Gestión de Datos</h2>
        <p className="text-sm text-gray-500 mt-1">
          Ingesta de nuevas transacciones — los modelos se re-entrenan automáticamente
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <PipelinePanel status={status} onRetrain={handleRetrain} />
        </div>
        <div className="lg:col-span-2">
          <IngestForm onSuccess={fetchStatus} />
        </div>
      </div>
    </div>
  )
}