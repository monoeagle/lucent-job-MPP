interface Props {
  id?: string
  label: string; value: number | undefined; onChange: (v: number) => void
  constraints: { min?: number; max?: number; step?: number; unit?: string }
  required?: boolean; description?: string | null; errors?: string[]
}
export default function IntegerField({ id, label, value, onChange, constraints, required, description, errors }: Props) {
  return (
    <div className="mb-3">
      <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-1">*</span>}
        {constraints.unit && <span className="text-gray-400 text-xs ml-1">({constraints.unit})</span>}
      </label>
      {description && <p className="text-xs text-gray-400 mb-1">{description}</p>}
      <input id={id} type="number" value={value ?? ''} onChange={(e) => onChange(Number(e.target.value))}
        min={constraints.min} max={constraints.max} step={constraints.step ?? 1}
        className={`w-full px-3 py-2 border rounded-md text-sm ${
          required && (value === undefined || value === null) ? 'border-red-400 bg-red-50' : 'border-gray-300'
        }`} />
      {constraints.min !== undefined && constraints.max !== undefined && (
        <p className="text-xs text-gray-400 mt-0.5">{constraints.min} – {constraints.max}</p>
      )}
      {errors?.map((e, i) => <p key={i} className="text-xs text-red-500 mt-0.5">{e}</p>)}
    </div>
  )
}
