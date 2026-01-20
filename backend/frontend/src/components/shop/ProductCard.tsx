import { Link } from 'react-router-dom'
import type { Product } from '../../app/types'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import Card from '../ui/Card'

export default function ProductCard({
  product,
  onAdd
}: {
  product: Product
  onAdd: (product: Product) => void
}) {
  const inStock = product.stock_quantity > 0

  return (
    <Card className="group overflow-hidden p-0">
      <div className="relative aspect-[4/3] overflow-hidden">
        <img
          src={product.image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=1200&q=80'}
          alt={product.name}
          className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
          loading="lazy"
        />
        <div className="absolute left-3 top-3">
          <Badge tone={inStock ? 'success' : 'warning'}>{inStock ? 'In stock' : 'Sold out'}</Badge>
        </div>
      </div>

      <div className="space-y-3 p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <Link to={`/products/${product.id}`} className="text-sm font-semibold hover:underline">
              {product.name}
            </Link>
            <div className="mt-1 text-xs text-slate-400">{product.category || 'General'}</div>
          </div>
          <div className="text-sm font-semibold">${Number(product.price).toFixed(2)}</div>
        </div>

        <div className="line-clamp-2 text-sm text-slate-300">
          {product.description || 'A clean, modern product crafted for everyday use.'}
        </div>

        <div className="flex items-center justify-between gap-3">
          <Link
            to={`/products/${product.id}`}
            className="text-sm text-slate-300 hover:text-white"
          >
            View details
          </Link>
          <Button disabled={!inStock} onClick={() => onAdd(product)}>
            Add to cart
          </Button>
        </div>
      </div>
    </Card>
  )
}