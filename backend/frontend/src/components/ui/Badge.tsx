import React from 'react'
import clsx from 'clsx'

type Variant = 'default' | 'success' | 'warning' | 'danger'

type Props = React.HTMLAttributes<HTMLSpanElement> & {
  /** @deprecated Use variant instead */
  tone?: 'neutral' | 'success' | 'warning'
  variant?: Variant
}

export default function Badge({ className, tone, variant, ...props }: Props) {
  // Support both tone (legacy) and variant (new)
  const v = variant ?? (tone === 'neutral' ? 'default' : tone) ?? 'default'

  const styles: Record<Variant, string> = {
    default: 'bg-white/10 text-slate-200 border-white/10',
    success: 'bg-emerald-500/15 text-emerald-200 border-emerald-400/20',
    warning: 'bg-amber-500/15 text-amber-200 border-amber-400/20',
    danger: 'bg-rose-500/15 text-rose-200 border-rose-400/20'
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full border px-2 py-0.5 text-xs',
        styles[v],
        className
      )}
      {...props}
    />
  )
}
