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
  showGroupHeaders?: boolean
}

export function isVisible(param: ParameterDefinition, values: Record<string, unknown>): boolean {
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

export function isFormComplete(parameters: ParameterDefinition[], values: Record<string, unknown>): boolean {
  for (const param of parameters) {
    if (!isVisible(param, values)) continue
    if (!param.required) continue

    const val = values[param.key]
    if (val === undefined || val === null || val === '') return false

    if (param.type === 'string' && typeof val === 'string') {
      if (!val.trim()) return false
      if (param.constraints.pattern && !new RegExp(param.constraints.pattern).test(val)) return false
    }
  }
  return true
}

export default function ParameterForm({ parameters, values, onChange, errors, showGroupHeaders = true }: Props) {
  const visible = parameters.filter(p => isVisible(p, values))
  const grouped = visible.reduce<Record<string, ParameterDefinition[]>>((acc, p) => {
    const g = p.group || 'Allgemein'
    if (!acc[g]) acc[g] = []
    acc[g].push(p)
    return acc
  }, {})

  function handleChange(param: ParameterDefinition, val: unknown) {
    onChange(param.key, val)

    // Auto-fill: if enum option has metadata, set affected fields
    if (param.type === 'enum' && param.affects_options_of.length > 0 && typeof val === 'string') {
      const option = param.constraints.options?.find(o => o.value === val)
      if (option?.metadata) {
        for (const [metaKey, metaVal] of Object.entries(option.metadata)) {
          if (param.affects_options_of.includes(metaKey)) {
            onChange(metaKey, metaVal)
          }
        }
      }
    }
  }

  function filterOptions(p: ParameterDefinition) {
    if (p.type !== 'enum' || !p.constraints.options) return p.constraints.options ?? []
    return p.constraints.options.filter(opt => {
      if (!opt.enabled) return false
      if (!opt.metadata) return true
      // Filter by metadata matching current values
      // e.g. metadata.security_areas=["sec1","sec2"] checks if values.security_area is in the list
      // e.g. metadata.allowed_system_types=["dc"] checks if values.system_type is in the list
      for (const [metaKey, metaVal] of Object.entries(opt.metadata)) {
        if (Array.isArray(metaVal)) {
          // Find which parameter this metadata refers to (by naming convention)
          // metadata key like "security_areas" → parameter key "security_area"
          // metadata key like "allowed_system_types" → parameter key "system_type"
          const paramKey = metaKey.replace(/s$/, '').replace('allowed_', '')
          const currentVal = values[paramKey]
          if (currentVal && !metaVal.includes(currentVal)) return false
        }
      }
      return true
    })
  }

  function renderField(p: ParameterDefinition) {
    const fieldErrors = errors?.[p.key]
    const v = values[p.key]
    const change = (val: unknown) => handleChange(p, val)

    const fieldId = `param-${p.key}`
    switch (p.type) {
      case 'integer': case 'range_integer': case 'float': case 'range_float':
        return <IntegerField key={p.key} id={fieldId} label={p.label} value={v as number | undefined}
          onChange={change as (v: number) => void} constraints={p.constraints}
          required={p.required} description={p.description} errors={fieldErrors} />
      case 'enum':
        return <EnumField key={p.key} id={fieldId} label={p.label} value={v as string | undefined}
          onChange={change as (v: string) => void} options={filterOptions(p)}
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
          {showGroupHeaders && (
            <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3 border-b pb-1">{group}</h4>
          )}
          {params.sort((a, b) => a.display_order - b.display_order).map(renderField)}
        </div>
      ))}
    </div>
  )
}
