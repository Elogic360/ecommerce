import React from 'react'
import clsx from 'clsx'

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
}

export default function Button({ className, variant = 'primary', ...props }: Props) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-indigo-400/60 disabled:opacity-50 disabled:cursor-not-allowed'

  const styles: Record<string, string> = {
    primary:
      'bg-white text-slate-900 hover:bg-slate-100 shadow-glow border border-white/10',
    secondary: 'bg-white/10 text-white hover:bg-white/15 border border-white/10',
    ghost: 'bg-transparent text-slate-200 hover:bg-white/5 border border-white/10',
    danger: 'bg-rose-500 text-white hover:bg-rose-400 border border-rose-300/20'
  }

  return <button className={clsx(base, styles[variant], className)} {...props} />
}
