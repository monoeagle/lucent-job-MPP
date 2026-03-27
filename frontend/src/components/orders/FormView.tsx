import type { ServiceTemplateDetail, ParameterDefinition } from '../../types/catalog'
import type { OrderContext } from '../../types/context'
import ContextSelector from './ContextSelector'
import ParameterForm from '../ParameterForm/ParameterForm'
import RequestSummary from './RequestSummary'

interface Props {
  template: ServiceTemplateDetail
  values: Record<string, unknown>
  context: OrderContext | null
  quantity: number
  onValuesChange: (key: string, value: unknown) => void
  onContextChange: (ctx: OrderContext) => void
  onQuantityChange: (q: number) => void
  onSubmit: () => void
  isSubmitting?: boolean
}

function getSectionOrder(template: ServiceTemplateDetail): Array<{ label: string; params: ParameterDefinition[] }> {
  const wizardConfig = template.metadata?.wizard_config as
    { steps?: Array<{ group: string; label: string }> } | undefined

  if (wizardConfig?.steps) {
    const sections: Array<{ label: string; params: ParameterDefinition[] }> = []
    const coveredGroups = new Set<string>()
    for (const stepDef of wizardConfig.steps) {
      const params = template.parameters.filter((p) => p.group === stepDef.group)
      if (params.length > 0) {
        sections.push({ label: stepDef.label, params })
        coveredGroups.add(stepDef.group)
      }
    }
    const uncovered = template.parameters.filter((p) => !coveredGroups.has(p.group ?? ''))
    if (uncovered.length > 0) {
      sections.push({ label: 'Weitere Parameter', params: uncovered })
    }
    return sections
  }

  const groups = new Map<string, ParameterDefinition[]>()
  for (const p of template.parameters) {
    const g = p.group ?? 'Allgemein'
    if (!groups.has(g)) groups.set(g, [])
    groups.get(g)!.push(p)
  }
  return [...groups.entries()]
    .sort((a, b) => Math.min(...a[1].map((p) => p.display_order)) - Math.min(...b[1].map((p) => p.display_order)))
    .map(([label, params]) => ({ label, params }))
}

export default function FormView({
  template, values, context, quantity,
  onValuesChange, onContextChange, onQuantityChange, onSubmit, isSubmitting,
}: Props) {
  const sections = getSectionOrder(template)

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold mb-4 border-b pb-2">Kontext</h3>
        <ContextSelector value={context} onChange={onContextChange} />
      </div>

      {sections.map((section) => (
        <div key={section.label}>
          <h3 className="text-lg font-semibold mb-4 border-b pb-2">{section.label}</h3>
          <ParameterForm
            parameters={section.params}
            values={values}
            onChange={onValuesChange}
            showGroupHeaders={false}
          />
        </div>
      ))}

      <div>
        <h3 className="text-lg font-semibold mb-4 border-b pb-2">Zusammenfassung</h3>
        <RequestSummary
          template={template}
          parameters={values}
          parameterDefs={template.parameters}
          quantity={quantity}
          onQuantityChange={onQuantityChange}
        />
        <button onClick={onSubmit} disabled={isSubmitting}
          className="mt-4 w-full px-4 py-2 bg-green-600 text-white rounded-md text-sm hover:bg-green-700 disabled:opacity-50">
          {isSubmitting ? 'Wird erstellt...' : 'Zur Bestellung hinzufügen'}
        </button>
      </div>
    </div>
  )
}
