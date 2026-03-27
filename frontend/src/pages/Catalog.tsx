import { useState } from 'react'
import { useTemplates, useTemplate, useCategories } from '../hooks/useCatalog'
import type { CatalogFilters } from '../api/catalog'
import FilterBar from '../components/catalog/FilterBar'
import TemplateCard from '../components/catalog/TemplateCard'
import TemplateDetail from '../components/catalog/TemplateDetail'
import Drawer from '../components/Drawer'

export default function Catalog() {
  const [filters, setFilters] = useState<CatalogFilters>({})
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)

  const { data: templates, isLoading } = useTemplates(filters)
  const { data: categories } = useCategories()
  const { data: detail } = useTemplate(selectedSlug)

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Service Catalog</h1>
        {templates && (
          <span className="text-sm text-gray-500">{templates.total} Services</span>
        )}
      </div>

      <FilterBar
        categories={categories?.categories ?? []}
        onFilterChange={(f) => setFilters({ ...filters, ...f })}
      />

      {isLoading && <p className="text-gray-500">Laden...</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {templates?.data.map((t) => (
          <TemplateCard key={t.id} template={t} onClick={() => setSelectedSlug(t.slug)} />
        ))}
      </div>

      {templates?.data.length === 0 && !isLoading && (
        <p className="text-gray-500 text-center py-8">Keine Services gefunden.</p>
      )}

      <Drawer open={!!selectedSlug} onClose={() => setSelectedSlug(null)}
              title={detail?.display_name ?? 'Laden...'}>
        {detail && <TemplateDetail template={detail} />}
      </Drawer>
    </div>
  )
}
