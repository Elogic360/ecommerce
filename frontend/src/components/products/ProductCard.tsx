/**
 * ProductCard - Enhanced product card with grid/list view support
 */
import React, { memo } from 'react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';
import { ShoppingCart, Heart, Star, Eye } from 'lucide-react';
import type { ProductSummary, ViewMode } from '../../types/product';
import { getImageUrl, formatPrice, calculateDiscount } from '../../services/productService';

interface ProductCardProps {
  product: ProductSummary;
  viewMode?: ViewMode;
  onAddToCart?: (product: ProductSummary) => void;
  onQuickView?: (product: ProductSummary) => void;
  onWishlist?: (product: ProductSummary) => void;
  isInWishlist?: boolean;
  className?: string;
}

const ProductCard: React.FC<ProductCardProps> = memo(({
  product,
  viewMode = 'grid',
  onAddToCart,
  onQuickView,
  onWishlist,
  isInWishlist = false,
  className,
}) => {
  const inStock = product.stock > 0;
  const isLowStock = product.stock > 0 && product.stock <= 5;
  const discount = calculateDiscount(product.price, product.original_price);
  const imageUrl = getImageUrl(product.primary_image || product.thumbnail);

  // Get stock status display info
  const getStockBadge = () => {
    if (!inStock) {
      return { text: 'Out of Stock', className: 'bg-gray-900/90 text-white' };
    }
    if (isLowStock) {
      return { text: `Only ${product.stock} left!`, className: 'bg-amber-500 text-white' };
    }
    return { text: `${product.stock} Available`, className: 'bg-green-500 text-white' };
  };

  const stockBadge = getStockBadge();

  const handleAddToCart = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onAddToCart && inStock) {
      onAddToCart(product);
    }
  };

  const handleQuickView = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onQuickView) {
      onQuickView(product);
    }
  };

  const handleWishlist = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onWishlist) {
      onWishlist(product);
    }
  };

  // Grid View
  if (viewMode === 'grid') {
    return (
      <article
        className={clsx(
          'group relative overflow-hidden rounded-xl bg-white shadow-sm border border-gray-100',
          'transition-all duration-300 hover:shadow-lg hover:-translate-y-1',
          className
        )}
      >
        {/* Image Container */}
        <Link to={`/products/${product.id}`} className="block">
          <div className="relative aspect-[4/3] overflow-hidden bg-gray-100">
            <img
              src={imageUrl}
              alt={product.name}
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
              loading="lazy"
              crossOrigin="anonymous"
              onError={(e) => {
                e.currentTarget.src = getImageUrl(null);
                e.currentTarget.onerror = null;
              }}
            />

            {/* Badges */}
            <div className="absolute left-3 top-3 flex flex-col gap-2">
              <span className={clsx(
                'rounded-full px-2.5 py-1 text-xs font-semibold shadow-sm',
                stockBadge.className
              )}>
                {stockBadge.text}
              </span>
              {discount > 0 && inStock && (
                <span className="rounded-full bg-red-500 px-2.5 py-1 text-xs font-medium text-white">
                  -{discount}%
                </span>
              )}
              {product.is_featured && (
                <span className="rounded-full bg-orange-500 px-2.5 py-1 text-xs font-medium text-white">
                  Featured
                </span>
              )}
            </div>

            {/* Action Buttons */}
            <div className="absolute right-3 top-3 flex flex-col gap-2 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
              {onWishlist && (
                <button
                  onClick={handleWishlist}
                  className={clsx(
                    'rounded-full p-2 shadow-md transition-colors',
                    isInWishlist
                      ? 'bg-red-500 text-white'
                      : 'bg-white text-gray-600 hover:bg-red-500 hover:text-white'
                  )}
                  aria-label={isInWishlist ? 'Remove from wishlist' : 'Add to wishlist'}
                >
                  <Heart className="h-4 w-4" fill={isInWishlist ? 'currentColor' : 'none'} />
                </button>
              )}
              {onQuickView && (
                <button
                  onClick={handleQuickView}
                  className="rounded-full bg-white p-2 text-gray-600 shadow-md transition-colors hover:bg-orange-500 hover:text-white"
                  aria-label="Quick view"
                >
                  <Eye className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        </Link>

        {/* Content */}
        <div className="p-4">
          {/* Category */}
          {product.category && (
            <span className="text-xs font-medium uppercase tracking-wide text-orange-500">
              {product.category}
            </span>
          )}

          {/* Title */}
          <Link to={`/products/${product.id}`}>
            <h3 className="mt-1 line-clamp-2 text-sm font-semibold text-gray-900 hover:text-orange-500 transition-colors">
              {product.name}
            </h3>
          </Link>

          {/* Rating */}
          {product.rating_count > 0 && (
            <div className="mt-2 flex items-center gap-1">
              <div className="flex">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star
                    key={i}
                    className={clsx(
                      'h-3.5 w-3.5',
                      i < Math.round(product.rating_average)
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'fill-gray-200 text-gray-200'
                    )}
                  />
                ))}
              </div>
              <span className="text-xs text-gray-500">
                ({product.rating_count})
              </span>
            </div>
          )}

          {/* Price */}
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-lg font-bold text-gray-900">
              {formatPrice(product.price)}
            </span>
            {product.original_price && product.original_price > product.price && (
              <span className="text-sm text-gray-400 line-through">
                {formatPrice(product.original_price)}
              </span>
            )}
          </div>

          {/* Add to Cart Button */}
          <button
            onClick={handleAddToCart}
            disabled={!inStock}
            className={clsx(
              'mt-4 flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition-colors',
              inStock
                ? 'bg-orange-500 text-white hover:bg-orange-600'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            )}
          >
            <ShoppingCart className="h-4 w-4" />
            {inStock ? 'Add to Cart' : 'Out of Stock'}
          </button>
        </div>
      </article>
    );
  }

  // List View
  return (
    <article
      className={clsx(
        'group flex gap-4 overflow-hidden rounded-xl bg-white p-4 shadow-sm border border-gray-100',
        'transition-all duration-300 hover:shadow-md',
        className
      )}
    >
      {/* Image */}
      <Link to={`/products/${product.id}`} className="relative flex-shrink-0">
        <div className="relative h-32 w-32 overflow-hidden rounded-lg bg-gray-100 sm:h-40 sm:w-40">
          <img
            src={imageUrl}
            alt={product.name}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
            crossOrigin="anonymous"
            onError={(e) => {
              e.currentTarget.src = getImageUrl(null);
              e.currentTarget.onerror = null;
            }}
          />

          {/* Badges */}
          {discount > 0 && (
            <span className="absolute left-2 top-2 rounded-full bg-red-500 px-2 py-0.5 text-xs font-medium text-white">
              -{discount}%
            </span>
          )}
        </div>
      </Link>

      {/* Content */}
      <div className="flex flex-1 flex-col justify-between">
        <div>
          {/* Category */}
          {product.category && (
            <span className="text-xs font-medium uppercase tracking-wide text-orange-500">
              {product.category}
            </span>
          )}

          {/* Title */}
          <Link to={`/products/${product.id}`}>
            <h3 className="mt-1 text-base font-semibold text-gray-900 hover:text-orange-500 transition-colors sm:text-lg">
              {product.name}
            </h3>
          </Link>

          {/* Rating */}
          {product.rating_count > 0 && (
            <div className="mt-2 flex items-center gap-1">
              <div className="flex">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star
                    key={i}
                    className={clsx(
                      'h-4 w-4',
                      i < Math.round(product.rating_average)
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'fill-gray-200 text-gray-200'
                    )}
                  />
                ))}
              </div>
              <span className="text-sm text-gray-500">
                {product.rating_average.toFixed(1)} ({product.rating_count} reviews)
              </span>
            </div>
          )}

          {/* Stock Status */}
          <div className="mt-2">
            <span className={clsx(
              'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold',
              !inStock ? 'bg-gray-100 text-gray-700' :
                isLowStock ? 'bg-amber-100 text-amber-700' :
                  'bg-green-100 text-green-700'
            )}>
              {stockBadge.text}
            </span>
          </div>
        </div>

        {/* Bottom Row */}
        <div className="mt-4 flex items-center justify-between">
          {/* Price */}
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold text-gray-900">
              {formatPrice(product.price)}
            </span>
            {product.original_price && product.original_price > product.price && (
              <span className="text-sm text-gray-400 line-through">
                {formatPrice(product.original_price)}
              </span>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {onWishlist && (
              <button
                onClick={handleWishlist}
                className={clsx(
                  'rounded-lg p-2 transition-colors',
                  isInWishlist
                    ? 'bg-red-50 text-red-500'
                    : 'bg-gray-100 text-gray-600 hover:bg-red-50 hover:text-red-500'
                )}
                aria-label={isInWishlist ? 'Remove from wishlist' : 'Add to wishlist'}
              >
                <Heart className="h-5 w-5" fill={isInWishlist ? 'currentColor' : 'none'} />
              </button>
            )}
            <button
              onClick={handleAddToCart}
              disabled={!inStock}
              className={clsx(
                'flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                inStock
                  ? 'bg-orange-500 text-white hover:bg-orange-600'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              )}
            >
              <ShoppingCart className="h-4 w-4" />
              <span className="hidden sm:inline">{inStock ? 'Add to Cart' : 'Out of Stock'}</span>
            </button>
          </div>
        </div>
      </div>
    </article>
  );
});

ProductCard.displayName = 'ProductCard';

export default ProductCard;
