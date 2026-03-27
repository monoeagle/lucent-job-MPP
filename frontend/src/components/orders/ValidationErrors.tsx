import type { ValidationViolation } from '../../types/order'

interface Props {
  errors: ValidationViolation[]
}

export default function ValidationErrors({ errors }: Props) {
  if (errors.length === 0) return null

  return (
    <ul className="mt-2 space-y-1">
      {errors.map((err, i) => (
        <li key={i} className="text-xs text-red-600 flex items-start gap-1">
          <span className="mt-0.5 shrink-0">&#x2717;</span>
          <span>
            <strong>{err.parameter_key}</strong>: {err.message}
            <span className="text-gray-400 ml-1">({err.rule})</span>
          </span>
        </li>
      ))}
    </ul>
  )
}
