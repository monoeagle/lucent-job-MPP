import type { ServiceTemplateDetail } from '../../types/catalog'
import StatusBadge from '../StatusBadge'
import ParameterList from './ParameterList'

interface Props {
  template: ServiceTemplateDetail
}

export default function TemplateDetail({ template }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <StatusBadge status={template.status} />
          <span className="text-xs text-gray-400">v{template.version}</span>
        </div>
        <p className="text-sm text-gray-600">{template.description}</p>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div><span className="text-gray-500">Typ:</span> {template.type}</div>
        <div><span className="text-gray-500">Kategorie:</span> {template.category}</div>
        <div><span className="text-gray-500">Slug:</span> <code className="text-xs bg-gray-100 px-1 rounded">{template.slug}</code></div>
        {template.estimated_cost_eur_per_month && (
          <div><span className="text-gray-500">Kosten:</span> ~{template.estimated_cost_eur_per_month} EUR/Monat</div>
        )}
      </div>

      {template.deprecated_by && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm">
          Dieses Template ist veraltet. Neuere Version: <strong>{template.deprecated_by.slug} v{template.deprecated_by.version}</strong>
        </div>
      )}

      <div>
        <h3 className="font-semibold mb-3">Parameter ({template.parameters.length})</h3>
        <ParameterList parameters={template.parameters} />
      </div>

      {template.cross_parameter_rules.length > 0 && (
        <div>
          <h3 className="font-semibold mb-2">Kombinationsregeln</h3>
          {template.cross_parameter_rules.map((r) => (
            <div key={r.rule_id} className="text-sm text-gray-600 bg-gray-50 rounded p-2 mb-1">
              {r.description}
            </div>
          ))}
        </div>
      )}

      <div className="text-xs text-gray-400">
        Tofu-Modul: <code>{template.tofu_module_source}</code>
      </div>
    </div>
  )
}
