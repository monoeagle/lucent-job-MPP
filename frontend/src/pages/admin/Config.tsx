import { useQuery } from '@tanstack/react-query'
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

function StatusDot({ status }: { status: string }) {
  const color = status === 'ok' ? 'bg-green-500' : status === 'error' ? 'bg-red-500' : 'bg-yellow-500'
  return <span className={`inline-block w-2.5 h-2.5 rounded-full ${color}`} />
}

function ConfigSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">{title}</h3>
      <div className="space-y-2 text-sm">{children}</div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-900 font-medium">{value}</span>
    </div>
  )
}

export default function Config() {
  const token = useAuthStore((s) => s.token)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-config'],
    queryFn: () => apiClient.get('/api/v1/admin/config', token!) as Promise<SystemConfig>,
    enabled: !!token,
  })

  if (isLoading) return <p className="text-sm text-gray-500">Laden...</p>
  if (!data) return <p className="text-sm text-gray-500">Keine Daten verfuegbar.</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Konfiguration</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ConfigSection title="Authentifizierung (AD/LDAP)">
          <Row label="Modus" value={<span className="flex items-center gap-2"><StatusDot status={data.auth.status} /> {data.auth.mode}</span>} />
          <Row label="Beschreibung" value={data.auth.description} />
        </ConfigSection>

        <ConfigSection title="CMDB">
          <Row label="Modus" value={<span className="flex items-center gap-2"><StatusDot status={data.cmdb.status} /> {data.cmdb.mode}</span>} />
          <Row label="Beschreibung" value={data.cmdb.description} />
          {data.cmdb.stub_data_path && <Row label="Datenpfad" value={data.cmdb.stub_data_path} />}
        </ConfigSection>

        <ConfigSection title="Datenbank">
          <Row label="Status" value={<StatusDot status={data.database.status} />} />
          <Row label="Verbindung" value={<span className="font-mono text-xs">{data.database.url}</span>} />
        </ConfigSection>

        <ConfigSection title="GitLab / CI Pipeline">
          <Row label="Status" value={<StatusDot status={data.gitlab.status} />} />
          <Row label="URL" value={data.gitlab.url} />
          {data.gitlab.project_id && <Row label="Projekt-ID" value={data.gitlab.project_id} />}
        </ConfigSection>

        <ConfigSection title="E-Mail / SMTP">
          <Row label="Status" value={<StatusDot status={data.email.status} />} />
          <Row label="Beschreibung" value={data.email.description} />
        </ConfigSection>

        <ConfigSection title="DSGVO">
          <Row label="Anonymisierung" value={data.dsgvo.anonymize ? 'Aktiviert' : 'Deaktiviert'} />
        </ConfigSection>

        <ConfigSection title="Genehmigungen">
          <Row label="Standard-Frist" value={`${data.approvals.default_deadline_hours} Stunden`} />
          <Row label="Selbst-Genehmigung" value={data.approvals.allow_self_approval ? 'Erlaubt' : 'Nicht erlaubt'} />
        </ConfigSection>
      </div>
    </div>
  )
}
