import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useTemplate } from '../hooks/useCatalog'
import { useCreateOrder } from '../hooks/useOrders'
import { useAuthStore } from '../store/authStore'
import type { OrderContext } from '../types/context'
import WizardView from '../components/orders/WizardView'
import FormView from '../components/orders/FormView'

type ViewMode = 'wizard' | 'form'

function getStoredView(slug: string): ViewMode | null {
  const stored = localStorage.getItem(`mpp-view-${slug}`)
  if (stored === 'wizard' || stored === 'form') return stored
  return null
}

function getDefaultView(metadata: Record<string, unknown> | undefined): ViewMode {
  const wc = metadata?.wizard_config as { preferred_view?: string } | undefined
  if (wc?.preferred_view === 'form') return 'form'
  const pv = metadata?.preferred_view
  if (pv === 'form') return 'form'
  return 'wizard'
}

export default function ServiceRequest() {
  const { slug } = useParams<{ slug: string }>()
  const [searchParams] = useSearchParams()
  const orderId = searchParams.get('orderId')
  const navigate = useNavigate()
  const { data: template, isLoading } = useTemplate(slug ?? null)

  const createOrder = useCreateOrder()
  const token = useAuthStore((s) => s.token)

  const [view, setView] = useState<ViewMode>('wizard')
  const [values, setValues] = useState<Record<string, unknown>>({})
  const [context, setContext] = useState<OrderContext | null>(null)
  const [quantity, setQuantity] = useState(1)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (template) {
      const stored = getStoredView(template.slug)
      setView(stored ?? getDefaultView(template.metadata))
    }
  }, [template])

  const toggleView = () => {
    const next = view === 'wizard' ? 'form' : 'wizard'
    setView(next)
    if (slug) localStorage.setItem(`mpp-view-${slug}`, next)
  }

  const handleSubmit = async () => {
    if (!template || !token) return
    const hasWizardConfig = !!(template.metadata?.wizard_config as { steps?: unknown[] } | undefined)?.steps
    if (!hasWizardConfig && !context) return
    setSubmitting(true)
    try {
      let targetOrderId = orderId
      if (!targetOrderId) {
        const orderBody: { title: string; context?: Record<string, string> } = {
          title: `${template.display_name} Bestellung`,
        }
        if (context) {
          orderBody.context = context as unknown as Record<string, string>
        }
        const order = await createOrder.mutateAsync(orderBody)
        targetOrderId = order.id
      }

      const { ordersApi } = await import('../api/orders')
      await ordersApi.addItem(token, targetOrderId, {
        template_slug: template.slug,
        template_version: template.version,
        parameters: values,
        quantity: quantity > 1 ? quantity : undefined,
      })

      navigate(`/orders/${targetOrderId}`)
    } finally {
      setSubmitting(false)
    }
  }

  if (isLoading) return <p className="text-gray-500">Lade Template...</p>
  if (!template) return <p className="text-red-500">Template nicht gefunden.</p>

  const viewProps = {
    template,
    values,
    context,
    quantity,
    onValuesChange: (key: string, val: unknown) => setValues((prev) => ({ ...prev, [key]: val })),
    onContextChange: setContext,
    onQuantityChange: setQuantity,
    onSubmit: handleSubmit,
    isSubmitting: submitting,
  }

  return (
    <div>
      <div className="flex justify-end mb-6">
        <button
          data-testid="view-toggle"
          onClick={toggleView}
          className="px-3 py-1.5 border border-gray-300 rounded-md text-sm text-gray-600 hover:bg-gray-50"
        >
          {view === 'wizard' ? '≡ Formular-Ansicht' : '☰ Wizard-Ansicht'}
        </button>
      </div>

      {view === 'wizard' ? <WizardView {...viewProps} /> : <FormView {...viewProps} />}
    </div>
  )
}
