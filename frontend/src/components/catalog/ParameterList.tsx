import type { ParameterDefinition } from '../../types/catalog'

interface Props {
  parameters: ParameterDefinition[]
}

export default function ParameterList({ parameters }: Props) {
  const grouped = parameters.reduce<Record<string, ParameterDefinition[]>>((acc, p) => {
    const group = p.group || 'Allgemein'
    if (!acc[group]) acc[group] = []
    acc[group].push(p)
    return acc
  }, {})

  return (
    <div className="space-y-4">
      {Object.entries(grouped).map(([group, params]) => (
        <div key={group}>
          <h4 className="text-sm font-medium text-gray-500 mb-2">{group}</h4>
          <div className="space-y-2">
            {params.sort((a, b) => a.display_order - b.display_order).map((p) => (
              <div key={p.key} className="flex justify-between items-center py-1 px-3 bg-gray-50 rounded text-sm">
                <div>
                  <span className="font-medium">{p.label}</span>
                  {p.required && <span className="text-red-500 ml-1">*</span>}
                  {p.description && <p className="text-xs text-gray-400">{p.description}</p>}
                </div>
                <div className="text-gray-500 text-xs">
                  {p.type}
                  {p.constraints.min !== undefined && p.constraints.max !== undefined && (
                    <span> ({p.constraints.min}–{p.constraints.max}{p.constraints.unit ? ` ${p.constraints.unit}` : ''})</span>
                  )}
                  {p.constraints.options && (
                    <span> ({p.constraints.options.filter(o => o.enabled).length} Optionen)</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
