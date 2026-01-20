import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { CartLine, Product } from '../types'

type CartState = {
  lines: CartLine[]
  add: (product: Product, qty?: number) => void
  remove: (productId: number) => void
  setQty: (productId: number, qty: number) => void
  clear: () => void
}

export const useCart = create<CartState>()(
  persist(
    (set, get) => ({
      lines: [],
      add: (product, qty = 1) => {
        const lines = [...get().lines]
        const idx = lines.findIndex((l) => l.product.id === product.id)
        if (idx >= 0) {
          lines[idx] = { ...lines[idx], quantity: Math.max(1, lines[idx].quantity + qty) }
        } else {
          lines.push({ product, quantity: Math.max(1, qty) })
        }
        set({ lines })
      },
      remove: (productId) => set({ lines: get().lines.filter((l) => l.product.id !== productId) }),
      setQty: (productId, qty) => {
        const lines = get().lines.map((l) =>
          l.product.id === productId ? { ...l, quantity: Math.max(1, qty) } : l
        )
        set({ lines })
      },
      clear: () => set({ lines: [] })
    }),
    { name: 'storefront_cart_v1' }
  )
)

export function cartSubtotal(lines: CartLine[]): number {
  return lines.reduce((sum, l) => sum + Number(l.product.price) * l.quantity, 0)
}