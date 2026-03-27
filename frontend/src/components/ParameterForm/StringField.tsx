interface Props {
  id?: string
  label: string; value: string | undefined; onChange: (v: string) => void
  constraints: { min_length?: number; max_length?: number; pattern?: string }
  required?: boolean; description?: string | null; errors?: string[]
}
export default function StringField({ id, label, value, onChange, constraints, required, description, errors }: Props) {
  return (
    <div className="mb-3">
      <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {description && <p className="text-xs text-gray-400 mb-1">{description}</p>}
      <input id={id} type="text" value={value ?? ''} onChange={(e) => onChange(e.target.value)}
        maxLength={constraints.max_length} pattern={constraints.pattern}
        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
      {errors?.map((e, i) => <p key={i} className="text-xs text-red-500 mt-0.5">{e}</p>)}
    </div>
  )
}
