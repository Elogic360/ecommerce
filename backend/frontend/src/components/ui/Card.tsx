import React from 'react'
import clsx from 'clsx'

type Props = React.HTMLAttributes<HTMLDivElement>

export default function Card({ className, ...props }: Props) {
  return (
    <div
      className={clsx(
        'rounded-2xl border border-white/10 bg-white/[0.03] p-5 shadow-glow',
        className
      )}
      {...props}
    />
  )
}