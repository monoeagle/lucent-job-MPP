import { useSearchParams, Link } from 'react-router-dom'
import OrderList from './OrderList'

type OrderTab = 'all' | 'mine'

const TABS: Array<{ key: OrderTab; label: string }> = [
  { key: 'all', label: 'Alle Bestellungen' },
  { key: 'mine', label: 'Meine Bestellungen' },
]

export default function Workspace() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = (searchParams.get('tab') as OrderTab) || 'all'

  const setTab = (tab: OrderTab) => {
    setSearchParams({ tab })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Bestellungen</h1>
        <Link to="/shop"
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700">
          Zum Shop
        </Link>
      </div>
      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <OrderList />
    </div>
  )
}
