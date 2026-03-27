interface Props {
  id?: string
  label: string; value: string | undefined; onChange: (v: string) => void
  constraints: { min_length?: number; max_length?: number; pattern?: string }
  required?: boolean; description?: string | null; errors?: string[]
}
export default function StringField({ id, label, value, onChange, constraints, required, description, errors }: Props) {
  const isEmpty = required && (!value || !value.trim())
  const patternInvalid = value && value.trim() && constraints.pattern
    ? !new RegExp(constraints.pattern).test(value)
    : false
  const isInvalid = isEmpty || patternInvalid

  return (
    <div className="mb-3">
      <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {description && <p className="text-xs text-gray-400 mb-1">{description}</p>}
      <input id={id} type="text" value={value ?? ''} onChange={(e) => onChange(e.target.value)}
        maxLength={constraints.max_length} pattern={constraints.pattern}
        className={`w-full px-3 py-2 border rounded-md text-sm ${
          isInvalid ? 'border-red-400 bg-red-50' : 'border-gray-300'
        }`} />
      {patternInvalid && (
        <p className="text-xs text-red-500 mt-0.5">Ungueltiges Format</p>
      )}
      {errors?.map((e, i) => <p key={i} className="text-xs text-red-500 mt-0.5">{e}</p>)}
    </div>
  )
}
