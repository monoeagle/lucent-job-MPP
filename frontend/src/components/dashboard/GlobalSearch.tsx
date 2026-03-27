import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSearch } from '../../hooks/useDashboard'

export default function GlobalSearch() {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const { data: results } = useSearch(debouncedQuery)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300)
    return () => clearTimeout(timer)
  }, [query])

  useEffect(() => {
    setOpen(debouncedQuery.length >= 2 && !!results)
  }, [debouncedQuery, results])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (type: string, id: string) => {
    setOpen(false)
    setQuery('')
    if (type === 'order') navigate(`/orders/${id}`)
    else if (type === 'template') navigate(`/shop/${id}/request`)
    else navigate('/my-services')
  }

  const hasResults = results && (results.orders.length > 0 || results.templates.length > 0)

  return (
    <div ref={ref} className="relative w-80">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
        placeholder="Suche..."
        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
        data-testid="global-search"
      />
      {open && results && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-80 overflow-auto">
          {!hasResults && (
            <p className="p-3 text-sm text-gray-400">Keine Ergebnisse</p>
          )}
          {results.orders.length > 0 && (
            <div>
              <p className="px-3 pt-2 text-xs font-semibold text-gray-400 uppercase">Orders</p>
              {results.orders.map((o) => (
                <button key={o.id} onClick={() => handleSelect('order', o.id)}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50">
                  {o.order_number} — {o.title}
                </button>
              ))}
            </div>
          )}
          {results.templates.length > 0 && (
            <div>
              <p className="px-3 pt-2 text-xs font-semibold text-gray-400 uppercase">Services</p>
              {results.templates.map((t) => (
                <button key={t.slug} onClick={() => handleSelect('template', t.slug)}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50">
                  {t.display_name} <span className="text-gray-400">({t.category})</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
