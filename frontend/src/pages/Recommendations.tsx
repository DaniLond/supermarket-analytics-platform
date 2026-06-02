import { useCallback, useEffect, useRef, useState } from 'react'
import { recommendationsApi } from '../services/apiClient'
import type {
  AssociationRule,
  CategoryRecommendationsResponse,
  CustomerRecommendationsResponse,
} from '../types'

// ---------------------------------------------------------------------------
// Helpers de presentación
// ---------------------------------------------------------------------------

type CatMap = Record<number, string>

function catLabel(id: number, map: CatMap) {
  const name = map[id]
  return name
    ? name.charAt(0) + name.slice(1).toLowerCase()
    : `Cat. ${id}`
}

function CatChip({ id, map, highlight = false }: { id: number; map: CatMap; highlight?: boolean }) {
  const base = highlight
    ? 'bg-blue-600 text-white'
    : 'bg-blue-100 text-blue-800'
  return (
    <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full mr-1 mb-1 ${base}`}>
      {catLabel(id, map)}
    </span>
  )
}

function CatList({ ids, map, highlight = false }: { ids: number[]; map: CatMap; highlight?: boolean }) {
  return <>{ids.map((id) => <CatChip key={id} id={id} map={map} highlight={highlight} />)}</>
}

function LiftBadge({ lift }: { lift: number }) {
  const color =
    lift >= 3 ? 'bg-green-100 text-green-800' :
    lift >= 1.5 ? 'bg-yellow-100 text-yellow-800' :
    'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-block text-xs font-semibold px-2 py-0.5 rounded-full ${color}`}>
      {lift.toFixed(2)}×
    </span>
  )
}

// ---------------------------------------------------------------------------
// Tabla de reglas
// ---------------------------------------------------------------------------

function RulesTable({ rules, map }: { rules: AssociationRule[]; map: CatMap }) {
  if (!rules.length)
    return <p className="text-sm text-gray-400 py-4">No se encontraron reglas para este criterio.</p>

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-gray-100 text-gray-500 uppercase tracking-wide text-left">
            <th className="py-2 pr-4 font-medium">Si compra</th>
            <th className="py-2 pr-4 font-medium">También compra</th>
            <th className="py-2 pr-3 text-right font-medium">Confianza</th>
            <th className="py-2 text-right font-medium">Lift</th>
          </tr>
        </thead>
        <tbody>
          {rules.map((r, i) => (
            <tr key={i} className="border-b border-gray-50 hover:bg-gray-50 align-top">
              <td className="py-2 pr-4"><CatList ids={r.antecedent} map={map} /></td>
              <td className="py-2 pr-4"><CatList ids={r.consequent} map={map} highlight /></td>
              <td className="py-2 pr-3 text-right font-medium text-gray-700 whitespace-nowrap">
                {(r.confidence * 100).toFixed(1)}%
              </td>
              <td className="py-2 text-right whitespace-nowrap">
                <LiftBadge lift={r.lift} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Panel: por categoría
// ---------------------------------------------------------------------------

function ByCategoryPanel({ map }: { map: CatMap }) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<CategoryRecommendationsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const search = async () => {
    const id = parseInt(input, 10)
    if (isNaN(id)) { setError('Ingresa un número de categoría válido.'); return }
    setLoading(true); setError(null); setResult(null)
    try {
      setResult(await recommendationsApi.byCategory(id))
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail ?? 'Error al consultar.')
    } finally {
      setLoading(false)
    }
  }

  const catName = result ? (map[result.category_id] ?? `Categoría ${result.category_id}`) : null

  return (
    <div>
      <p className="text-xs text-gray-500 mb-4">
        Ingresa el ID de una categoría para ver qué otras categorías suelen comprarse junto a ella.
      </p>

      {/* Selector de categorías disponibles */}
      <div className="mb-4 flex flex-wrap gap-1">
        {Object.entries(map)
          .sort(([a], [b]) => Number(a) - Number(b))
          .map(([id, name]) => (
            <button
              key={id}
              onClick={() => setInput(id)}
              className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                input === id
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-600'
              }`}
            >
              {name.charAt(0) + name.slice(1).toLowerCase()}
            </button>
          ))}
      </div>

      <div className="flex gap-2 mb-5">
        <input
          type="number"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()}
          placeholder="ID de categoría"
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-blue-300"
        />
        <button
          onClick={search}
          disabled={loading}
          className="bg-blue-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Buscando…' : 'Buscar'}
        </button>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-4">
          {error}
        </p>
      )}

      {result && (
        <>
          <p className="text-xs text-gray-500 mb-3">
            <strong>{result.rules.length}</strong> regla{result.rules.length !== 1 ? 's' : ''} encontrada{result.rules.length !== 1 ? 's' : ''} para{' '}
            <strong>{catName}</strong>
          </p>
          <RulesTable rules={result.rules} map={map} />
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Panel: por cliente
// ---------------------------------------------------------------------------

function ByCustomerPanel({ map }: { map: CatMap }) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<CustomerRecommendationsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const search = async () => {
    const id = parseInt(input, 10)
    if (isNaN(id)) { setError('Ingresa un número de cliente válido.'); return }
    setLoading(true); setError(null); setResult(null)
    try {
      setResult(await recommendationsApi.byCustomer(id))
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string }; status?: number } }
      if (err.response?.status === 404) {
        setError(`No se encontraron recomendaciones para el cliente ${id}. Puede que no tenga historial o que ya compre todas las categorías sugeridas.`)
      } else {
        setError(err.response?.data?.detail ?? 'Error al consultar.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <p className="text-xs text-gray-500 mb-4">
        Ingresa el ID de un cliente para ver categorías recomendadas basadas en su historial de compras y reglas FP-Growth.
      </p>

      <div className="flex gap-2 mb-5">
        <input
          type="number"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()}
          placeholder="ID de cliente (ej. 530)"
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-blue-300"
        />
        <button
          onClick={search}
          disabled={loading}
          className="bg-blue-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Buscando…' : 'Buscar'}
        </button>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-4">
          {error}
        </p>
      )}

      {result && (
        <div className="space-y-5">
          {/* Cabecera del cliente */}
          <div className="flex flex-wrap gap-3 items-start">
            <div className="bg-gray-50 rounded-lg px-4 py-2 text-xs">
              <p className="text-gray-500">Cliente</p>
              <p className="font-semibold text-gray-800 text-sm">{result.customer_id}</p>
            </div>
            {result.cluster !== null && (
              <div className="bg-gray-50 rounded-lg px-4 py-2 text-xs">
                <p className="text-gray-500">Segmento K-Means</p>
                <p className="font-semibold text-gray-800 text-sm">Clúster {result.cluster}</p>
              </div>
            )}
          </div>

          {/* Recomendaciones */}
          {result.recommended_categories.length > 0 ? (
            <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
              <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-2">
                Categorías recomendadas ({result.recommended_categories.length})
              </p>
              <div className="flex flex-wrap gap-1">
                {result.recommended_categories.map((id) => (
                  <span
                    key={id}
                    className="inline-block bg-blue-600 text-white text-xs font-medium px-3 py-1 rounded-full"
                  >
                    {catLabel(id, map)}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-500 italic">
              El cliente ya compra todas las categorías sugeridas por las reglas disponibles.
            </p>
          )}

          {/* Reglas usadas */}
          <div>
            <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">
              Reglas aplicadas ({result.rules_used.length})
            </p>
            <RulesTable rules={result.rules_used} map={map} />
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Página principal
// ---------------------------------------------------------------------------

type Phase = 'checking' | 'training' | 'ready' | 'error'
type Tab = 'category' | 'customer'
interface RecStatus { ready: boolean; training: boolean; error: string | null }

export default function Recommendations() {
  const [phase, setPhase] = useState<Phase>('checking')
  const [trainError, setTrainError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('category')
  const [catMap, setCatMap] = useState<CatMap>({})
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null }
  }, [])

  useEffect(() => {
    async function checkStatus() {
      try {
        const s: RecStatus = await recommendationsApi.status()
        if (s.ready) {
          stopPolling()
          setPhase('ready')
          // Cargar mapa de categorías una sola vez
          recommendationsApi.categories().then(setCatMap).catch(() => {})
        } else if (s.error) {
          stopPolling()
          setTrainError(s.error)
          setPhase('error')
        } else {
          setPhase('training')
          if (!intervalRef.current)
            intervalRef.current = setInterval(checkStatus, 10_000)
        }
      } catch {
        if (!intervalRef.current)
          intervalRef.current = setInterval(checkStatus, 10_000)
      }
    }

    checkStatus()
    return stopPolling
  }, [stopPolling])

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Recomendaciones</h2>
        <p className="text-sm text-gray-500 mt-1">
          Reglas de asociación FP-Growth entrenadas sobre canastas de compra
        </p>
      </div>

      {phase === 'checking' && (
        <div className="flex items-center gap-3 text-gray-500 text-sm py-12 justify-center">
          <span className="animate-spin text-lg">⟳</span>
          Verificando estado del modelo…
        </div>
      )}

      {phase === 'training' && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-8 flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-blue-800 font-medium text-sm">Entrenando reglas FP-Growth con PySpark…</p>
          <p className="text-blue-600 text-xs text-center max-w-sm">
            El proceso analiza todas las canastas de compra y extrae patrones de co-ocurrencia.
            La página se actualizará automáticamente al terminar.
          </p>
        </div>
      )}

      {phase === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6">
          <p className="text-red-800 font-medium text-sm mb-2">El entrenamiento FP-Growth falló</p>
          <pre className="text-red-700 text-xs bg-red-100 rounded p-3 overflow-auto max-h-48 whitespace-pre-wrap">
            {trainError}
          </pre>
          <p className="text-red-600 text-xs mt-3">
            Revisa los logs con <code className="bg-red-100 px-1 rounded">docker compose logs backend</code>
          </p>
        </div>
      )}

      {phase === 'ready' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="flex border-b border-gray-100">
            {(['category', 'customer'] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-6 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
                  tab === t
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {t === 'category' ? 'Por Categoría' : 'Por Cliente'}
              </button>
            ))}
          </div>

          <div className="p-6">
            {tab === 'category'
              ? <ByCategoryPanel map={catMap} />
              : <ByCustomerPanel map={catMap} />}
          </div>
        </div>
      )}
    </div>
  )
}