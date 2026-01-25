import { useState, useRef, useCallback } from 'react';
import { ChevronLeft, ChevronRight, ZoomIn, X, Maximize2 } from 'lucide-react';
import type { ProductImage } from '@/types/product';
import { getImageUrl } from '@/app/api';

interface ImageGalleryProps {
  images: ProductImage[];
  productName: string;
}

export function ImageGallery({ images, productName }: ImageGalleryProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isZoomed, setIsZoomed] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [zoomPosition, setZoomPosition] = useState({ x: 0, y: 0 });
  const imageRef = useRef<HTMLDivElement>(null);

  const selectedImage = images[selectedIndex] || {
    url: '/placeholder-product.png',
    alt_text: productName,
  };

  const handlePrevious = useCallback(() => {
    setSelectedIndex((prev) => (prev > 0 ? prev - 1 : images.length - 1));
  }, [images.length]);

  const handleNext = useCallback(() => {
    setSelectedIndex((prev) => (prev < images.length - 1 ? prev + 1 : 0));
  }, [images.length]);

  const handleThumbnailClick = (index: number) => {
    setSelectedIndex(index);
  };

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!imageRef.current || !isZoomed) return;

    const rect = imageRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    setZoomPosition({ x, y });
  }, [isZoomed]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowLeft':
        handlePrevious();
        break;
      case 'ArrowRight':
        handleNext();
        break;
      case 'Escape':
        if (isFullscreen) {
          setIsFullscreen(false);
        }
        break;
    }
  }, [handlePrevious, handleNext, isFullscreen]);

  const toggleFullscreen = () => {
    setIsFullscreen((prev) => !prev);
    setIsZoomed(false);
  };

  if (images.length === 0) {
    return (
      <div className="aspect-square bg-slate-800 rounded-lg flex items-center justify-center">
        <span className="text-slate-500 text-lg">No image available</span>
      </div>
    );
  }

  const GalleryContent = (
    <div
      className={`${isFullscreen ? 'fixed inset-0 z-50 bg-black flex flex-col' : ''}`}
      onKeyDown={handleKeyDown}
      tabIndex={0}
    >
      {/* Fullscreen header */}
      {isFullscreen && (
        <div className="flex justify-between items-center p-4 bg-black/50">
          <span className="text-white font-medium">
            {selectedIndex + 1} / {images.length}
          </span>
          <button
            onClick={() => setIsFullscreen(false)}
            className="p-2 text-white hover:bg-white/10 rounded-lg transition-colors"
            aria-label="Close fullscreen"
          >
            <X className="h-6 w-6" />
          </button>
        </div>
      )}

      {/* Main image container */}
      <div className={`relative ${isFullscreen ? 'flex-1 flex items-center justify-center' : ''}`}>
        <div
          ref={imageRef}
          className={`
            relative overflow-hidden rounded-lg bg-slate-800
            ${isFullscreen ? 'max-w-4xl max-h-[80vh] mx-auto' : 'aspect-square'}
            ${isZoomed ? 'cursor-zoom-out' : 'cursor-zoom-in'}
          `}
          onClick={() => setIsZoomed(!isZoomed)}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setIsZoomed(false)}
        >
          <img
            src={getImageUrl(selectedImage.url)}
            alt={selectedImage.alt_text || productName}
            className={`
              w-full h-full object-contain transition-transform duration-200
              ${isZoomed ? 'scale-150' : 'scale-100'}
              ${isZoomed ? `origin-[${zoomPosition.x}%_${zoomPosition.y}%]` : ''}
            `}
            loading="lazy"
            crossOrigin="anonymous"
            onError={(e) => {
              e.currentTarget.src = getImageUrl(null);
              e.currentTarget.onerror = null;
            }}
          />

          {/* Zoom indicator */}
          {!isZoomed && !isFullscreen && (
            <div className="absolute bottom-4 right-4 bg-black/50 text-white p-2 rounded-lg text-sm flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <ZoomIn className="h-4 w-4" />
              Click to zoom
            </div>
          )}

          {/* Fullscreen button */}
          {!isFullscreen && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleFullscreen();
              }}
              className="absolute top-4 right-4 p-2 bg-black/50 text-white rounded-lg hover:bg-black/70 transition-colors"
              aria-label="View fullscreen"
            >
              <Maximize2 className="h-5 w-5" />
            </button>
          )}
        </div>

        {/* Navigation arrows */}
        {images.length > 1 && (
          <>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handlePrevious();
              }}
              className={`
                absolute left-2 top-1/2 -translate-y-1/2 p-2 rounded-full
                bg-black/50 text-white hover:bg-black/70 transition-colors
                ${isFullscreen ? 'left-4' : ''}
              `}
              aria-label="Previous image"
            >
              <ChevronLeft className="h-6 w-6" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleNext();
              }}
              className={`
                absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full
                bg-black/50 text-white hover:bg-black/70 transition-colors
                ${isFullscreen ? 'right-4' : ''}
              `}
              aria-label="Next image"
            >
              <ChevronRight className="h-6 w-6" />
            </button>
          </>
        )}
      </div>

      {/* Thumbnails */}
      {images.length > 1 && (
        <div
          className={`
            flex gap-2 mt-4 overflow-x-auto pb-2
            ${isFullscreen ? 'justify-center px-4' : ''}
          `}
        >
          {images.map((image, index) => (
            <button
              key={image.id || index}
              onClick={() => handleThumbnailClick(index)}
              className={`
                flex-shrink-0 rounded-lg overflow-hidden transition-all
                ${isFullscreen ? 'w-16 h-16' : 'w-20 h-20'}
                ${index === selectedIndex
                  ? 'ring-2 ring-emerald-500 ring-offset-2 ring-offset-slate-900'
                  : 'ring-1 ring-slate-700 opacity-60 hover:opacity-100'
                }
              `}
              aria-label={`View image ${index + 1}`}
              aria-current={index === selectedIndex ? 'true' : undefined}
            >
              <img
                src={getImageUrl(image.url)}
                alt={image.alt_text || `${productName} - Image ${index + 1}`}
                className="w-full h-full object-cover"
                loading="lazy"
                crossOrigin="anonymous"
                onError={(e) => {
                  e.currentTarget.src = getImageUrl(null);
                  e.currentTarget.onerror = null;
                }}
              />
            </button>
          ))}
        </div>
      )}

      {/* Image counter (mobile) */}
      {images.length > 1 && !isFullscreen && (
        <div className="flex justify-center gap-1.5 mt-3 md:hidden">
          {images.map((_, index) => (
            <button
              key={index}
              onClick={() => handleThumbnailClick(index)}
              className={`
                w-2 h-2 rounded-full transition-colors
                ${index === selectedIndex ? 'bg-emerald-500' : 'bg-slate-600'}
              `}
              aria-label={`Go to image ${index + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  );

  return <div className="group">{GalleryContent}</div>;
}

export default ImageGallery;
