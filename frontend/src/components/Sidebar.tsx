import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Resumen Ejecutivo' },
  { to: '/analytics', label: 'Visualizaciones' },
  { to: '/advanced', label: 'Análisis Avanzado' },
]

export default function Sidebar() {
  return (
    <aside className="w-56 bg-brand-700 text-white flex flex-col shrink-0">
      <div className="px-6 py-5 border-b border-brand-600">
        <h1 className="text-lg font-bold leading-tight">Supermercado<br />Analytics</h1>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-brand-500 text-white'
                  : 'text-brand-100 hover:bg-brand-600 hover:text-white'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
