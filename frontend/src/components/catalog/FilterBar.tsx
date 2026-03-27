import { useState } from 'react'
import type { CategoryItem } from '../../types/catalog'

interface Props {
  categories: CategoryItem[]
  onFilterChange: (filters: { type?: string; category?: string; q?: string }) => void
}

export default function FilterBar({ categories, onFilterChange }: Props) {
  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedType, setSelectedType] = useState('')

  function handleSearchChange(value: string) {
    setSearch(value)
    onFilterChange({ q: value, category: selectedCategory, type: selectedType })
  }

  function handleCategoryChange(value: string) {
    setSelectedCategory(value)
    onFilterChange({ q: search, category: value, type: selectedType })
  }

  function handleTypeChange(value: string) {
    setSelectedType(value)
    onFilterChange({ q: search, category: selectedCategory, type: value })
  }

  return (
    <div className="flex gap-4 mb-6 flex-wrap items-end">
      <div>
        <label className="block text-xs text-gray-500 mb-1">Suche</label>
        <input
          type="text"
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder="Service suchen..."
          className="px-3 py-2 border border-gray-300 rounded-md text-sm w-64"
        />
      </div>
      <div>
        <label className="block text-xs text-gray-500 mb-1">Kategorie</label>
        <select value={selectedCategory} onChange={(e) => handleCategoryChange(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm">
          <option value="">Alle</option>
          {categories.map((c) => (
            <option key={c.name} value={c.name}>{c.name} ({c.template_count})</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-xs text-gray-500 mb-1">Typ</label>
        <select value={selectedType} onChange={(e) => handleTypeChange(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm">
          <option value="">Alle</option>
          <option value="vm">VM</option>
          <option value="database">Database</option>
          <option value="container">Container</option>
          <option value="storage">Storage</option>
          <option value="network">Network</option>
        </select>
      </div>
    </div>
  )
}
