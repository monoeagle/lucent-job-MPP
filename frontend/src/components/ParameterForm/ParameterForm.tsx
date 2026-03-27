import type { ParameterDefinition } from '../../types/catalog'
import IntegerField from './IntegerField'
import EnumField from './EnumField'
import BooleanField from './BooleanField'
import StringField from './StringField'
import SizeBytesField from './SizeBytesField'

interface Props {
  parameters: ParameterDefinition[]
  values: Record<string, unknown>
  onChange: (key: string, value: unknown) => void
  errors?: Record<string, string[]>
}

function isVisible(param: ParameterDefinition, values: Record<string, unknown>): boolean {
  const visRules = param.depends_on.filter(r => r.effect === 'visible')
  if (visRules.length === 0) return true
  return visRules.every(r => {
    const actual = values[r.parameter_key]
    switch (r.operator) {
      case 'eq': return actual === r.value
      case 'neq': return actual !== r.value
      case 'in': return Array.isArray(r.value) && r.value.includes(actual)
      case 'gt': return typeof actual === 'number' && actual > (r.value as number)
      default: return true
    }
  })
}

export default function ParameterForm({ parameters, values, onChange, errors }: Props) {
  const visible = parameters.filter(p => isVisible(p, values))
  const grouped = visible.reduce<Record<string, ParameterDefinition[]>>((acc, p) => {
    const g = p.group || 'Allgemein'
    if (!acc[g]) acc[g] = []
    acc[g].push(p)
    return acc
  }, {})

  function renderField(p: ParameterDefinition) {
    const fieldErrors = errors?.[p.key]
    const v = values[p.key]
    const change = (val: unknown) => onChange(p.key, val)

    const fieldId = `param-${p.key}`
    switch (p.type) {
      case 'integer': case 'range_integer': case 'float': case 'range_float':
        return <IntegerField key={p.key} id={fieldId} label={p.label} value={v as number | undefined}
          onChange={change as (v: number) => void} constraints={p.constraints}
          required={p.required} description={p.description} errors={fieldErrors} />
      case 'enum':
        return <EnumField key={p.key} id={fieldId} label={p.label} value={v as string | undefined}
          onChange={change as (v: string) => void} options={p.constraints.options ?? []}
          required={p.required} description={p.description} errors={fieldErrors} />
      case 'boolean':
        return <BooleanField key={p.key} id={fieldId} label={p.label} value={v as boolean | undefined}
          onChange={change as (v: boolean) => void} description={p.description} />
      case 'size_bytes':
        return <SizeBytesField key={p.key} id={fieldId} label={p.label} value={v as number | undefined}
          onChange={change as (v: number) => void} constraints={p.constraints}
          required={p.required} description={p.description} errors={fieldErrors} />
      default:
        return <StringField key={p.key} id={fieldId} label={p.label} value={v as string | undefined}
          onChange={change as (v: string) => void} constraints={p.constraints}
          required={p.required} description={p.description} errors={fieldErrors} />
    }
  }

  return (
    <div>
      {Object.entries(grouped).map(([group, params]) => (
        <div key={group} className="mb-6">
          <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3 border-b pb-1">{group}</h4>
          {params.sort((a, b) => a.display_order - b.display_order).map(renderField)}
        </div>
      ))}
    </div>
  )
}
