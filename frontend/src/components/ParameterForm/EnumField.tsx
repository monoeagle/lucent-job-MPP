import type { EnumOption } from '../../types/catalog'
interface Props {
  id?: string
  label: string; value: string | undefined; onChange: (v: string) => void
  options: EnumOption[]; required?: boolean; description?: string | null; errors?: string[]
}
export default function EnumField({ id, label, value, onChange, options, required, description, errors }: Props) {
  return (
    <div className="mb-3">
      <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {description && <p className="text-xs text-gray-400 mb-1">{description}</p>}
      <select id={id} value={value ?? ''} onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
        <option value="">Bitte wählen...</option>
        {options.filter(o => o.enabled).map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
      {errors?.map((e, i) => <p key={i} className="text-xs text-red-500 mt-0.5">{e}</p>)}
    </div>
  )
}
