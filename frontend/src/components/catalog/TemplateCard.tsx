import type { ServiceTemplate } from '../../types/catalog'
import StatusBadge from '../StatusBadge'

interface Props {
  template: ServiceTemplate
  onClick: () => void
}

export default function TemplateCard({ template, onClick }: Props) {
  return (
    <div onClick={onClick}
         className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md hover:border-blue-300 cursor-pointer transition-all">
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-semibold text-gray-900">{template.display_name}</h3>
        <StatusBadge status={template.status} />
      </div>
      <p className="text-sm text-gray-500 mb-3 line-clamp-2">{template.description}</p>
      <div className="flex gap-2 text-xs text-gray-400">
        <span className="bg-gray-100 px-2 py-0.5 rounded">{template.type}</span>
        <span className="bg-gray-100 px-2 py-0.5 rounded">{template.category}</span>
        <span className="bg-gray-100 px-2 py-0.5 rounded">v{template.version}</span>
      </div>
      {template.estimated_cost_eur_per_month && (
        <p className="text-xs text-gray-400 mt-2">~{template.estimated_cost_eur_per_month} EUR/Monat</p>
      )}
    </div>
  )
}
