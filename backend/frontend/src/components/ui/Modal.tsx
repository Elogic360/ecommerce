import React from 'react'
import Button from './Button'

type Props = {
  /** @deprecated Use isOpen instead */
  open?: boolean
  isOpen?: boolean
  title: string
  children: React.ReactNode
  onClose: () => void
  footer?: React.ReactNode
}

export default function Modal({ open, isOpen, title, children, onClose, footer }: Props) {
  // Support both open (legacy) and isOpen (new)
  const visible = isOpen ?? open ?? false

  if (!visible) return null

  return (
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div className="w-full max-w-lg rounded-2xl border border-white/10 bg-slate-950 shadow-glow max-h-[90vh] overflow-y-auto">
          <div className="flex items-start justify-between gap-4 border-b border-white/10 p-5 sticky top-0 bg-slate-950">
            <div>
              <div className="text-base font-semibold">{title}</div>
            </div>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white transition"
              aria-label="Close"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="p-5">{children}</div>
          {footer ? <div className="border-t border-white/10 p-5">{footer}</div> : null}
        </div>
      </div>
    </div>
  )
}