import QuantitySelector from './QuantitySelector'

interface Props {
  template: { display_name: string; version: string; estimated_cost_eur_per_month?: number | null }
  parameters: Record<string, unknown>
  parameterDefs: Array<{ key: string; label: string; group?: string | null }>
  quantity: number
  onQuantityChange: (q: number) => void
}

export default function RequestSummary({ template, parameters, parameterDefs, quantity, onQuantityChange }: Props) {
  const totalCost = template.estimated_cost_eur_per_month
    ? template.estimated_cost_eur_per_month * quantity
    : null

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h3 className="text-lg font-semibold">{template.display_name}</h3>
        <span className="text-sm text-gray-400">v{template.version}</span>
      </div>

      <div className="bg-gray-50 rounded-lg p-4 space-y-2">
        {parameterDefs
          .filter((p) => parameters[p.key] !== undefined && parameters[p.key] !== '')
          .map((p) => (
            <div key={p.key} className="flex justify-between text-sm">
              <span className="text-gray-600">{p.label}</span>
              <span className="font-medium">{String(parameters[p.key])}</span>
            </div>
          ))}
      </div>

      <QuantitySelector value={quantity} onChange={onQuantityChange} />

      {totalCost !== null && (
        <p className="text-sm text-gray-500">
          Geschaetzte Kosten: <span className="font-semibold">{totalCost} EUR/Monat</span>
          {quantity > 1 && ` (${quantity} × ${template.estimated_cost_eur_per_month} EUR)`}
        </p>
      )}
    </div>
  )
}
