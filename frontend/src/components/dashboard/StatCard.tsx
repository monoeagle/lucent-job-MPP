interface Props {
  label: string
  value: number
  color?: string
}

export default function StatCard({ label, value, color = 'text-blue-600' }: Props) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3">
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-xs text-gray-500 mt-1 leading-tight">{label}</p>
    </div>
  )
}
