import { useState } from 'react'
import type { ServiceTemplateDetail, ParameterDefinition } from '../../types/catalog'
import type { OrderContext } from '../../types/context'
import StepIndicator, { type StepDef } from './StepIndicator'
import ContextSelector from './ContextSelector'
import ParameterForm, { isFormComplete } from '../ParameterForm/ParameterForm'
import RequestSummary from './RequestSummary'

interface WizardStep extends StepDef {
  type: 'context' | 'params' | 'summary'
  params?: ParameterDefinition[]
}

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

function buildSteps(template: ServiceTemplateDetail): WizardStep[] {
  const steps: WizardStep[] = []

  const wizardConfig = template.metadata?.wizard_config as
    { steps?: Array<{ group: string; label: string }> } | undefined

  // Only add Context step if no wizard_config (template controls the full flow)
  if (!wizardConfig?.steps) {
    steps.push({ key: 'context', label: 'Kontext', type: 'context' })
  }

  if (wizardConfig?.steps) {
    for (const stepDef of wizardConfig.steps) {
      const params = template.parameters.filter((p) => p.group === stepDef.group)
      if (params.length > 0) {
        steps.push({ key: stepDef.group, label: stepDef.label, type: 'params', params })
      }
    }
    const coveredGroups = new Set(wizardConfig.steps.map((s) => s.group))
    const uncovered = template.parameters.filter((p) => !coveredGroups.has(p.group ?? ''))
    if (uncovered.length > 0) {
      const groups = [...new Set(uncovered.map((p) => p.group ?? 'Allgemein'))]
      for (const g of groups) {
        steps.push({ key: g, label: g, type: 'params', params: uncovered.filter((p) => (p.group ?? 'Allgemein') === g) })
      }
    }
  } else {
    const groups = new Map<string, ParameterDefinition[]>()
    for (const p of template.parameters) {
      const g = p.group ?? 'Allgemein'
      if (!groups.has(g)) groups.set(g, [])
      groups.get(g)!.push(p)
    }
    const sorted = [...groups.entries()].sort(
      (a, b) => Math.min(...a[1].map((p) => p.display_order)) - Math.min(...b[1].map((p) => p.display_order))
    )
    for (const [g, params] of sorted) {
      steps.push({ key: g, label: g, type: 'params', params })
    }
  }

  steps.push({ key: 'summary', label: 'Zusammenfassung', type: 'summary' })
  return steps
}

export default function WizardView({
  template, values, context, quantity,
  onValuesChange, onContextChange, onQuantityChange, onSubmit, isSubmitting,
}: Props) {
  const [currentStep, setCurrentStep] = useState(0)
  const steps = buildSteps(template)
  const step = steps[currentStep]
  const hasWizardConfig = !!(template.metadata?.wizard_config as { steps?: unknown[] } | undefined)?.steps

  const canNext = currentStep < steps.length - 1
  const canBack = currentStep > 0

  return (
    <div>
      <StepIndicator
        steps={steps}
        currentStep={currentStep}
        onStepClick={(i) => setCurrentStep(i)}
      />

      <div className="mt-6 min-h-[300px]">
        {step.type === 'context' && (
          <div>
            <ContextSelector value={context} onChange={onContextChange} />
          </div>
        )}

        {step.type === 'params' && step.params && (
          <div>
            <ParameterForm
              parameters={step.params}
              values={values}
              onChange={onValuesChange}
              showGroupHeaders={false}
            />
          </div>
        )}

        {step.type === 'summary' && (
          <div>
            <RequestSummary
              template={template}
              parameters={values}
              parameterDefs={template.parameters}
              quantity={quantity}
              onQuantityChange={onQuantityChange}
            />
          </div>
        )}
      </div>

      <div className="flex justify-between mt-6 pt-4 border-t">
        {canBack ? (
          <button onClick={() => setCurrentStep(currentStep - 1)}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
            ← Zurück
          </button>
        ) : <div />}

        {canNext ? (
          <button onClick={() => setCurrentStep(currentStep + 1)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700">
            Weiter
          </button>
        ) : (
          <button onClick={onSubmit}
            disabled={isSubmitting || (!context && !hasWizardConfig) || !isFormComplete(template.parameters, values)}
            className="px-4 py-2 bg-green-600 text-white rounded-md text-sm hover:bg-green-700 disabled:opacity-50"
            title={!context ? 'Kontext muss ausgefuellt sein' : !isFormComplete(template.parameters, values) ? 'Alle Pflichtfelder muessen ausgefuellt sein' : ''}>
            {isSubmitting ? 'Wird erstellt...' : 'Zur Bestellung hinzufügen'}
          </button>
        )}
      </div>
    </div>
  )
}
