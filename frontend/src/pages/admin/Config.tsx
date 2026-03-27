import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../../store/authStore'
import { apiClient } from '../../api/client'

interface SystemConfig {
  auth: { mode: string; status: string; description: string }
  cmdb: { mode: string; status: string; stub_data_path: string; description: string }
  database: { url: string; status: string }
  gitlab: { url: string; project_id: string; status: string }
  email: { status: string; description: string }
  dsgvo: { anonymize: boolean }
  approvals: { default_deadline_hours: number; allow_self_approval: boolean }
}

interface FormState {
  gitlab_url: string
  gitlab_project_id: string
  dsgvo_anonymize: boolean
  approval_default_deadline_hours: number
  approval_allow_self_approval: boolean
}

function StatusDot({ status }: { status: string }) {
  const color = status === 'ok' ? 'bg-green-500' : status === 'error' ? 'bg-red-500' : 'bg-yellow-500'
  return <span className={`inline-block w-2.5 h-2.5 rounded-full ${color}`} />
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">{title}</h3>
      <div className="space-y-3 text-sm">{children}</div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-900 font-medium">{value}</span>
    </div>
  )
}

export default function Config() {
  const token = useAuthStore((s) => s.token)
  const queryClient = useQueryClient()
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-config'],
    queryFn: () => apiClient.get('/api/v1/admin/config', token!) as Promise<SystemConfig>,
    enabled: !!token,
  })

  const [form, setForm] = useState<FormState>({
    gitlab_url: '',
    gitlab_project_id: '',
    dsgvo_anonymize: false,
    approval_default_deadline_hours: 48,
    approval_allow_self_approval: false,
  })

  // Sync form state when data loads
  useEffect(() => {
    if (data) {
      setForm({
        gitlab_url: data.gitlab.url === '(nicht konfiguriert)' ? '' : data.gitlab.url,
        gitlab_project_id: data.gitlab.project_id,
        dsgvo_anonymize: data.dsgvo.anonymize,
        approval_default_deadline_hours: data.approvals.default_deadline_hours,
        approval_allow_self_approval: data.approvals.allow_self_approval,
      })
    }
  }, [data])

  const saveMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      apiClient.put('/api/v1/admin/config', body, token!) as Promise<{ updated: string[]; message: string }>,
    onSuccess: (resp) => {
      queryClient.invalidateQueries({ queryKey: ['admin-config'] })
      setFeedback({ type: 'success', message: resp.message })
      setTimeout(() => setFeedback(null), 3000)
    },
    onError: () => {
      setFeedback({ type: 'error', message: 'Speichern fehlgeschlagen.' })
      setTimeout(() => setFeedback(null), 3000)
    },
  })

  const handleSave = () => {
    saveMutation.mutate(form)
  }

  if (isLoading) return <p className="text-sm text-gray-500">Laden...</p>
  if (!data) return <p className="text-sm text-gray-500">Keine Daten verfuegbar.</p>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Konfiguration</h1>
        <button
          onClick={handleSave}
          disabled={saveMutation.isPending}
          className="px-5 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {saveMutation.isPending ? 'Speichert...' : 'Speichern'}
        </button>
      </div>

      {feedback && (
        <div className={`mb-4 p-3 rounded-md text-sm border ${
          feedback.type === 'success'
            ? 'bg-green-50 text-green-700 border-green-200'
            : 'bg-red-50 text-red-700 border-red-200'
        }`}>
          {feedback.message}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Read-only: Auth */}
        <Section title="Authentifizierung (AD/LDAP)">
          <Row label="Modus" value={<span className="flex items-center gap-2"><StatusDot status={data.auth.status} /> {data.auth.mode}</span>} />
          <Row label="Beschreibung" value={data.auth.description} />
          <p className="text-xs text-gray-400 pt-1">Aenderung ueber Umgebungsvariable AUTH_MODE</p>
        </Section>

        {/* Read-only: CMDB */}
        <Section title="CMDB">
          <Row label="Modus" value={<span className="flex items-center gap-2"><StatusDot status={data.cmdb.status} /> {data.cmdb.mode}</span>} />
          <Row label="Beschreibung" value={data.cmdb.description} />
          {data.cmdb.stub_data_path && <Row label="Datenpfad" value={data.cmdb.stub_data_path} />}
          <p className="text-xs text-gray-400 pt-1">Aenderung ueber Umgebungsvariable CMDB_MODE</p>
        </Section>

        {/* Read-only: Database */}
        <Section title="Datenbank">
          <Row label="Status" value={<StatusDot status={data.database.status} />} />
          <Row label="Verbindung" value={<span className="font-mono text-xs">{data.database.url}</span>} />
          <p className="text-xs text-gray-400 pt-1">Aenderung ueber Umgebungsvariable DATABASE_URL</p>
        </Section>

        {/* Editable: GitLab */}
        <Section title="GitLab / CI Pipeline">
          <Row label="Status" value={<StatusDot status={data.gitlab.status} />} />
          <div>
            <label className="block text-gray-500 mb-1">URL</label>
            <input
              type="text"
              value={form.gitlab_url}
              onChange={(e) => setForm((f) => ({ ...f, gitlab_url: e.target.value }))}
              placeholder="https://gitlab.example.com"
              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
            />
          </div>
          <div>
            <label className="block text-gray-500 mb-1">Projekt-ID</label>
            <input
              type="text"
              value={form.gitlab_project_id}
              onChange={(e) => setForm((f) => ({ ...f, gitlab_project_id: e.target.value }))}
              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
            />
          </div>
        </Section>

        {/* Read-only: Email */}
        <Section title="E-Mail / SMTP">
          <Row label="Status" value={<StatusDot status={data.email.status} />} />
          <Row label="Beschreibung" value={data.email.description} />
        </Section>

        {/* Editable: DSGVO */}
        <Section title="DSGVO">
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-gray-500">Anonymisierung</span>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.dsgvo_anonymize}
                onChange={(e) => setForm((f) => ({ ...f, dsgvo_anonymize: e.target.checked }))}
                className="w-4 h-4 rounded border-gray-300"
              />
              <span>{form.dsgvo_anonymize ? 'Aktiviert' : 'Deaktiviert'}</span>
            </div>
          </label>
        </Section>

        {/* Editable: Approvals */}
        <Section title="Genehmigungen">
          <div>
            <label className="block text-gray-500 mb-1">Standard-Frist (Stunden)</label>
            <input
              type="number"
              min={1}
              max={720}
              value={form.approval_default_deadline_hours}
              onChange={(e) => setForm((f) => ({ ...f, approval_default_deadline_hours: Number(e.target.value) }))}
              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
            />
          </div>
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-gray-500">Selbst-Genehmigung</span>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.approval_allow_self_approval}
                onChange={(e) => setForm((f) => ({ ...f, approval_allow_self_approval: e.target.checked }))}
                className="w-4 h-4 rounded border-gray-300"
              />
              <span>{form.approval_allow_self_approval ? 'Erlaubt' : 'Nicht erlaubt'}</span>
            </div>
          </label>
        </Section>
      </div>
    </div>
  )
}
