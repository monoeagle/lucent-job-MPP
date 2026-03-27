interface Props {
  id?: string
  label: string; value: boolean | undefined; onChange: (v: boolean) => void
  required?: boolean; description?: string | null
}
export default function BooleanField({ id, label, value, onChange, description }: Props) {
  return (
    <div className="mb-3 flex items-center gap-3">
      <input id={id} type="checkbox" checked={value ?? false} onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-gray-300" />
      <div>
        <label htmlFor={id} className="text-sm font-medium text-gray-700">{label}</label>
        {description && <p className="text-xs text-gray-400">{description}</p>}
      </div>
    </div>
  )
}
