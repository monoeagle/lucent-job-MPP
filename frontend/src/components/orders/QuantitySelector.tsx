interface Props {
  value: number
  onChange: (value: number) => void
}

export default function QuantitySelector({ value, onChange }: Props) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">Anzahl</label>
      <input
        type="number"
        min={1}
        max={50}
        value={value}
        onChange={(e) => onChange(Math.max(1, Math.min(50, parseInt(e.target.value) || 1)))}
        className="w-24 px-3 py-2 border border-gray-300 rounded-md text-sm"
      />
      {value > 1 && (
        <p className="text-xs text-gray-500 mt-1">{value} Instanzen werden erstellt.</p>
      )}
    </div>
  )
}
