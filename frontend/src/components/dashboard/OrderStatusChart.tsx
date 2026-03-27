import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const STATUS_COLORS: Record<string, string> = {
  draft: '#9CA3AF',
  submitted: '#3B82F6',
  pending_approval: '#F59E0B',
  provisioning: '#8B5CF6',
  done: '#10B981',
  failed: '#EF4444',
}

interface Props {
  data: Record<string, number>
}

export default function OrderStatusChart({ data }: Props) {
  const chartData = Object.entries(data)
    .filter(([, count]) => count > 0)
    .map(([status, count]) => ({ name: status, value: count }))

  if (chartData.length === 0) {
    return <p className="text-sm text-gray-400">Keine Orders vorhanden</p>
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Orders nach Status</h3>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
          >
            {chartData.map((entry) => (
              <Cell key={entry.name} fill={STATUS_COLORS[entry.name] ?? '#6B7280'} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
