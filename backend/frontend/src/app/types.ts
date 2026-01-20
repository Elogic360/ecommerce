export type Product = {
  id: number
  name: string
  description?: string | null
  category?: string | null
  price: string
  stock_quantity: number
  is_active: boolean
  image_url?: string | null
}

export type CartLine = {
  product: Product
  quantity: number
}

export type CustomerInfo = {
  name: string
  email: string
  phone?: string
}

export type OrderItemCreate = {
  product_id: number
  quantity: number
}

export type OrderCreate = {
  customer_name: string
  customer_email: string
  customer_phone?: string
  items: OrderItemCreate[]
  payment_method: 'card' | 'upi' | 'wallet' | 'cod'
}

export type OrderItem = {
  id: number
  product_id: number
  quantity: number
  price: string
}

export type Order = {
  id: number
  customer_id: number
  total_amount: string
  payment_status: string
  order_status: string
  items: OrderItem[]
}

export type Payment = {
  id: number
  order_id: number
  payment_method: string
  status: string
  provider_ref?: string | null
}
