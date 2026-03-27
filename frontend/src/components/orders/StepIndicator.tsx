export interface StepDef {
  key: string
  label: string
}

interface Props {
  steps: StepDef[]
  currentStep: number
  onStepClick: (index: number) => void
}

export default function StepIndicator({ steps, currentStep, onStepClick }: Props) {
  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-2">
      {steps.map((step, i) => {
        const status = i < currentStep ? 'completed' : i === currentStep ? 'current' : 'pending'
        const clickable = status === 'completed'

        return (
          <div key={step.key} className="flex items-center">
            {i > 0 && <div className={`w-6 h-px mx-1 ${status === 'pending' ? 'bg-gray-300' : 'bg-blue-500'}`} />}
            <button
              data-testid="step-item"
              data-status={status}
              disabled={!clickable}
              onClick={() => clickable && onStepClick(i)}
              className={`px-3 py-1.5 rounded-full text-xs whitespace-nowrap transition-colors ${
                status === 'completed'
                  ? 'bg-blue-100 text-blue-700 hover:bg-blue-200 cursor-pointer'
                  : status === 'current'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-400 cursor-default'
              }`}
            >
              {status === 'completed' ? '✓ ' : ''}{step.label}
            </button>
          </div>
        )
      })}
    </div>
  )
}
