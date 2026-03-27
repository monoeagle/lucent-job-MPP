import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface Props {
  data: Array<{ month: string; count: number }>
}

export default function OrderTimelineChart({ data }: Props) {
  if (data.length === 0) {
    return <p className="text-sm text-gray-400">Keine Daten vorhanden</p>
  }

  const formatted = data.map((d) => ({
    ...d,
    label: d.month.slice(5),
  }))

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Orders ueber Zeit</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={formatted}>
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="count"
            stroke="#3B82F6"
            strokeWidth={2}
            dot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
