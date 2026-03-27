const UNITS = { MB: 1024 * 1024, GB: 1024 * 1024 * 1024, TB: 1024 * 1024 * 1024 * 1024 }
interface Props {
  id?: string
  label: string; value: number | undefined; onChange: (v: number) => void
  constraints: { min_bytes?: number; max_bytes?: number; display_unit?: string }
  required?: boolean; description?: string | null; errors?: string[]
}
export default function SizeBytesField({ id, label, value, onChange, constraints, required, description, errors }: Props) {
  const unit = (constraints.display_unit ?? 'GB') as keyof typeof UNITS
  const multiplier = UNITS[unit] ?? UNITS.GB
  const displayValue = value !== undefined ? Math.round(value / multiplier) : ''

  return (
    <div className="mb-3">
      <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {description && <p className="text-xs text-gray-400 mb-1">{description}</p>}
      <div className="flex items-center gap-2">
        <input id={id} type="number" value={displayValue}
          onChange={(e) => onChange(Number(e.target.value) * multiplier)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm" />
        <span className="text-sm text-gray-500">{unit}</span>
      </div>
      {errors?.map((e, i) => <p key={i} className="text-xs text-red-500 mt-0.5">{e}</p>)}
    </div>
  )
}
