import Button from '../ui/Button'

export default function QtyPicker({
  value,
  onChange,
  max
}: {
  value: number
  onChange: (next: number) => void
  max?: number
}) {
  const canDec = value > 1
  const canInc = max == null ? true : value < max

  return (
    <div className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 p-1">
      <Button variant="ghost" disabled={!canDec} onClick={() => onChange(value - 1)}>
        −
      </Button>
      <div className="min-w-10 text-center text-sm font-semibold">{value}</div>
      <Button variant="ghost" disabled={!canInc} onClick={() => onChange(value + 1)}>
        +
      </Button>
    </div>
  )
}
