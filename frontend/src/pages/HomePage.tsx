import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ShoppingCart, 
  Search, 
  Star, 
  Sparkles, 
  Zap, 
  Package,
  Truck,
  Shield,
  ArrowRight,
  Clock,
  Flame,
  Phone,
  MapPin,
  Droplet,
  Wind,
  Trash,
  ShoppingBag
} from 'lucide-react';
import { productsAPI, cartAPI, getImageUrl } from '@/app/api';
import { useStore } from '@/app/store';
import { useCart } from '@/app/store/cart';
import { useToast } from '@/components/admin/Toast';

interface Product {
  id: number;
  name: string;
  price: number;
  original_price?: number;
  stock: number;
  rating?: number;
  review_count?: number;
  primary_image?: string;
  brand?: string;
  is_featured?: boolean;
  is_new?: boolean;
  is_bestseller?: boolean;
}

const Homepage: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [featuredProducts, setFeaturedProducts] = useState<Product[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { token, setCart } = useStore();
  const { add: addToLocalCart } = useCart();
  const { showToast } = useToast();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // Load featured products - API returns {items: [...], meta: {...}}
      const featuredResponse = await productsAPI.getAll({ 
        is_featured: true, 
        limit: 3 
      });
      const featuredData = featuredResponse.data?.items || featuredResponse.data || [];
      setFeaturedProducts(Array.isArray(featuredData) ? featuredData : []);

      // Load all products - API returns {items: [...], meta: {...}}
      const productsResponse = await productsAPI.getAll({ 
        limit: 12,
        sort_by: 'created_at',
        sort_order: 'desc'
      });
      const productsData = productsResponse.data?.items || productsResponse.data || [];
      setProducts(Array.isArray(productsData) ? productsData : []);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCart = async (productId: number) => {
    // Find the product to get its details
    const product = [...products, ...featuredProducts].find(p => p.id === productId);
    if (!product) return;

    if (token) {
      // Logged in - use API cart
      try {
        await cartAPI.add({ product_id: productId, quantity: 1 });
        // Reload cart and update store
        const cartResponse = await cartAPI.get();
        const cartData = cartResponse.data;
        if (cartData && cartData.items) {
          setCart(cartData.items.map((item: any) => ({
            id: item.id,
            product_id: item.product_id,
            quantity: item.quantity,
            product: item.product
          })));
        }
        showToast('Product added to cart!', 'success');
      } catch (error: any) {
        // If 401 (unauthorized/expired token), fall back to local cart
        if (error?.response?.status === 401) {
          console.log('Token expired, using local cart');
          addToLocalCart({
            id: product.id,
            name: product.name,
            price: String(product.price),
            stock_quantity: 100,
            is_active: true,
            image_url: product.primary_image,
          }, 1);
          showToast('Product added to cart!', 'success');
        } else {
          console.error('Error adding to cart:', error);
          showToast('Failed to add product to cart', 'error');
        }
      }
    } else {
      // Not logged in - use local cart
      addToLocalCart({
        id: product.id,
        name: product.name,
        price: String(product.price),
        stock_quantity: 100, // Default stock for local cart
        is_active: true,
        image_url: product.primary_image,
      }, 1);
      alert('Product added to cart!');
    }
  };

  const handleSearch = async () => {
    if (!searchTerm.trim()) return;
    
    try {
      const response = await productsAPI.getAll({ search: searchTerm, limit: 20 });
      const searchData = response.data?.items || response.data || [];
      setProducts(Array.isArray(searchData) ? searchData : []);
    } catch (error) {
      console.error('Error searching:', error);
    }
  };

  const handleProductClick = (productId: number) => {
    navigate(`/products/${productId}`);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gray-900 text-white sticky top-0 z-50">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center space-x-8">
              <h1 className="text-2xl font-bold text-orange-500 cursor-pointer" onClick={() => navigate('/')}>Neatify</h1>
              <nav className="hidden md:flex space-x-6">
                <a href="#" className="hover:text-orange-400 transition">Today's Deals</a>
                <a href="#" className="hover:text-orange-400 transition">New Arrivals</a>
                <a href="#" className="hover:text-orange-400 transition">Best Sellers</a>
              </nav>
            </div>

            <div className="flex-1 max-w-2xl mx-8">
              <div className="flex">
                <input
                  type="text"
                  placeholder="Search Neatify"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1 px-4 py-2 rounded-l-md text-black focus:outline-none"
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                />
                <button
                  onClick={handleSearch}
                  className="bg-orange-500 px-6 py-2 rounded-r-md hover:bg-orange-600 transition"
                  aria-label="Search products"
                >
                  <Search size={20} />
                </button>
              </div>
            </div>

            <div className="flex items-center space-x-6">
              <button 
                onClick={() => navigate(token ? '/profile' : '/login')}
                className="hover:text-orange-400 transition text-left"
              >
                <span className="text-sm">{token ? 'My Account' : 'Hello, Sign in'}</span>
                <div className="font-semibold">{token ? 'Profile' : 'Account & Lists'}</div>
              </button>
              <button 
                onClick={() => navigate('/orders')}
                className="hover:text-orange-400 transition text-left"
              >
                <span className="text-sm">Returns</span>
                <div className="font-semibold">& Orders</div>
              </button>
              <button 
                onClick={() => navigate('/cart')}
                className="relative hover:text-orange-400 transition"
              >
                <ShoppingCart size={28} />
                <span className="absolute -top-2 -right-2 bg-orange-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs font-bold">
                  0
                </span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Banner */}
      <section className="relative bg-gradient-to-r from-orange-600 via-orange-500 to-yellow-500 overflow-hidden">
        <div className="absolute inset-0 bg-black/10"></div>
        
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-10 left-10 animate-bounce">
            <ShoppingBag size={60} className="text-white" />
          </div>
          <div className="absolute bottom-20 right-20 animate-pulse">
            <Wind size={80} className="text-white" />
          </div>
          <div className="absolute top-1/3 right-1/4 animate-spin-slow">
            <Sparkles size={50} className="text-yellow-200" />
          </div>
        </div>

        <div className="container mx-auto px-4 py-8 relative z-10">
          <div className="grid md:grid-cols-2 gap-6 items-center">
            {/* Left Content */}
            <div className="text-white space-y-4">
              <div className="flex items-center space-x-3 mb-2">
                <Sparkles className="text-yellow-200 animate-pulse" size={24} />
                <span className="text-yellow-100 font-bold uppercase tracking-wider text-sm">Shop with Neatify</span>
              </div>
              
              <h1 className="text-4xl md:text-5xl font-extrabold leading-tight">
                Neatify
              </h1>
              
              <p className="text-xl md:text-2xl font-semibold text-orange-100">
                Your one-stop shop for everything you need
              </p>
              
              <p className="text-lg text-white/90">
                Quality Cleaning Supplies & Tools - Making Clean Easy
              </p>

              {/* Features Grid */}
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="flex items-center space-x-2 bg-white/10 backdrop-blur-sm rounded-lg p-2">
                  <ShoppingBag className="text-yellow-200" size={20} />
                  <span className="font-semibold text-xs">Cleaning Agents</span>
                </div>
                <div className="flex items-center space-x-2 bg-white/10 backdrop-blur-sm rounded-lg p-2">
                  <Wind className="text-yellow-200" size={20} />
                  <span className="font-semibold text-xs">Air Fresheners</span>
                </div>
                <div className="flex items-center space-x-2 bg-white/10 backdrop-blur-sm rounded-lg p-2">
                  <Droplet className="text-yellow-200" size={20} />
                  <span className="font-semibold text-xs">Detergents</span>
                </div>
                <div className="flex items-center space-x-2 bg-white/10 backdrop-blur-sm rounded-lg p-2">
                  <Trash className="text-yellow-200" size={20} />
                  <span className="font-semibold text-xs">Waste Solutions</span>
                </div>
              </div>

              {/* CTA Buttons */}
              <div className="flex flex-wrap gap-3 pt-2">
                <button 
                  onClick={() => navigate('/products')}
                  className="bg-white text-orange-600 px-6 py-2.5 rounded-xl font-bold hover:bg-gray-100 transition-all shadow-2xl flex items-center gap-2 text-sm hover:scale-105"
                >
                  Shop Now <ArrowRight size={18} />
                </button>
                <button 
                  onClick={() => navigate('/products')}
                  className="border-2 border-white text-white px-6 py-2.5 rounded-xl font-semibold hover:bg-white/10 transition-all text-sm"
                >
                  Discover Great Deals
                </button>
              </div>

              {/* Contact Info */}
              <div className="flex flex-col space-y-2 pt-2 bg-white/10 backdrop-blur-sm rounded-xl p-3">
                <div className="flex items-center space-x-2">
                  <Phone className="text-yellow-200" size={16} />
                  <div className="flex gap-3 text-xs font-medium">
                    <a href="tel:0719883695" className="hover:text-yellow-200 transition">0719 883 695</a>
                    <span>|</span>
                    <a href="tel:0685395844" className="hover:text-yellow-200 transition">0685 395 844</a>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <MapPin className="text-yellow-200" size={16} />
                  <span className="text-xs font-medium">BIASHARA COMPLEX, Komakoma</span>
                </div>
              </div>
            </div>

            {/* Right Image */}
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-yellow-400/20 to-orange-600/20 rounded-3xl blur-3xl"></div>
              <img 
                src="/neatify1.png" 
                alt="Neatify - Cleaning Supplies" 
                className="relative w-full h-auto rounded-2xl shadow-2xl border-4 border-white/20"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Featured Products */}
      <section className="bg-gradient-to-b from-orange-50 to-white py-12">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center space-x-3">
              <div className="bg-orange-500 p-2 rounded-lg">
                <Flame className="text-white" size={24} />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Featured Deals</h2>
                <p className="text-gray-600 text-sm">Handpicked products just for you</p>
              </div>
            </div>
            <button 
              onClick={() => navigate('/products')}
              className="text-orange-600 font-semibold hover:text-orange-700 flex items-center gap-1"
            >
              See All <ArrowRight size={16} />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {featuredProducts.map((product) => {
              const isOutOfStock = product.stock === 0;
              return (
                <div 
                  key={product.id} 
                  className={`bg-white rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden cursor-pointer group ${isOutOfStock ? 'opacity-80' : ''}`}
                  onClick={() => handleProductClick(product.id)}
                >
                  <div className="relative overflow-hidden">
                    <img
                      src={getImageUrl(product.primary_image) || '/placeholder-product.svg'}
                      alt={product.name}
                      className={`w-full h-72 object-cover group-hover:scale-105 transition-transform duration-300 ${isOutOfStock ? 'grayscale' : ''}`}
                    />
                    {/* Badges */}
                    <div className="absolute top-4 left-4 flex flex-col gap-2">
                      {product.original_price && product.original_price > product.price && (
                        <span className="bg-red-500 text-white px-3 py-1 rounded-full text-xs font-bold shadow">
                          {Math.round((1 - product.price / product.original_price) * 100)}% OFF
                        </span>
                      )}
                      {product.is_new && (
                        <span className="bg-blue-500 text-white px-3 py-1 rounded-full text-xs font-bold shadow">
                          NEW
                        </span>
                      )}
                      {product.is_bestseller && (
                        <span className="bg-purple-500 text-white px-3 py-1 rounded-full text-xs font-bold shadow">
                          BESTSELLER
                        </span>
                      )}
                    </div>
                    {/* Stock Badge */}
                    <div className="absolute top-4 right-4">
                      {isOutOfStock ? (
                        <span className="bg-gray-800 text-white px-3 py-1 rounded-full text-xs font-bold shadow">
                          OUT OF STOCK
                        </span>
                      ) : product.stock <= 5 ? (
                        <span className="bg-yellow-500 text-white px-3 py-1 rounded-full text-xs font-bold shadow animate-pulse">
                          Only {product.stock} left!
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <div className="p-5">
                    {product.brand && (
                      <div className="text-sm text-orange-600 font-semibold mb-1 uppercase tracking-wide">{product.brand}</div>
                    )}
                    <h3 className="font-bold text-lg mb-2 line-clamp-2 text-gray-900 group-hover:text-orange-600 transition-colors">{product.name}</h3>
                    <div className="flex items-center mb-3">
                      <div className="flex items-center text-yellow-500">
                        {[...Array(5)].map((_, i) => (
                          <Star key={i} size={14} fill={i < Math.round(product.rating || 0) ? 'currentColor' : 'none'} />
                        ))}
                      </div>
                      <span className="ml-2 text-sm font-semibold text-gray-700">{Number(product.rating || 0).toFixed(1)}</span>
                      <span className="text-gray-500 text-sm ml-1">({Number(product.review_count || 0).toLocaleString()} reviews)</span>
                    </div>
                    <div className="flex items-baseline space-x-2 mb-4">
                      <span className="text-2xl font-extrabold text-orange-600">
                        TZS {Number(product.price || 0).toLocaleString()}
                      </span>
                      {product.original_price && product.original_price > product.price && (
                        <span className="text-gray-400 line-through text-lg">
                          TZS {Number(product.original_price).toLocaleString()}
                        </span>
                      )}
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!isOutOfStock) handleAddToCart(product.id);
                      }}
                      disabled={isOutOfStock}
                      className={`w-full py-3 rounded-xl font-bold transition-all flex items-center justify-center gap-2 ${
                        isOutOfStock 
                          ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                          : 'bg-orange-500 text-white hover:bg-orange-600 hover:shadow-lg'
                      }`}
                    >
                      <ShoppingCart size={18} />
                      {isOutOfStock ? 'Out of Stock' : 'Add to Cart'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* All Products */}
      <section className="container mx-auto px-4 py-12">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-3">
            <div className="bg-gray-800 p-2 rounded-lg">
              <Package className="text-white" size={24} />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">All Products</h2>
              <p className="text-gray-600 text-sm">Explore our complete collection</p>
            </div>
          </div>
          <button 
            onClick={() => navigate('/products')}
            className="bg-gray-900 text-white px-6 py-2 rounded-lg font-semibold hover:bg-gray-800 transition flex items-center gap-2"
          >
            View All Products <ArrowRight size={16} />
          </button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-5">
          {products.map((product) => {
            const isOutOfStock = product.stock === 0;
            return (
              <div 
                key={product.id} 
                className={`group bg-white rounded-xl shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden cursor-pointer border border-gray-100 hover:border-orange-200 ${isOutOfStock ? 'opacity-75' : ''}`}
                onClick={() => handleProductClick(product.id)}
              >
                <div className="relative aspect-square overflow-hidden bg-gray-50">
                  <img
                    src={getImageUrl(product.primary_image) || '/placeholder-product.svg'}
                    alt={product.name}
                    className={`w-full h-full object-cover group-hover:scale-110 transition-transform duration-300 ${isOutOfStock ? 'grayscale' : ''}`}
                  />
                  {/* Stock Badge */}
                  {isOutOfStock ? (
                    <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                      <span className="bg-gray-900 text-white px-3 py-1 rounded-full text-xs font-bold">
                        OUT OF STOCK
                      </span>
                    </div>
                  ) : product.stock <= 5 ? (
                    <div className="absolute bottom-2 left-2">
                      <span className="bg-yellow-500 text-white px-2 py-0.5 rounded text-xs font-bold">
                        Only {product.stock} left
                      </span>
                    </div>
                  ) : null}
                  {/* Quick Add Button */}
                  {!isOutOfStock && (
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAddToCart(product.id);
                        }}
                        className="bg-orange-500 text-white px-4 py-2 rounded-lg font-semibold hover:bg-orange-600 transition transform scale-90 group-hover:scale-100 shadow-lg"
                      >
                        <ShoppingCart size={18} />
                      </button>
                    </div>
                  )}
                </div>
                <div className="p-3">
                  <h3 className="font-semibold text-sm mb-1 line-clamp-2 text-gray-900 group-hover:text-orange-600 transition-colors min-h-[2.5rem]">{product.name}</h3>
                  <div className="flex items-center text-yellow-500 text-xs mb-2">
                    <Star size={12} fill="currentColor" />
                    <span className="ml-1 text-gray-700 font-medium">{Number(product.rating || 0).toFixed(1)}</span>
                    <span className="text-gray-400 ml-1">({Number(product.review_count || 0)})</span>
                  </div>
                  <div className="font-bold text-orange-600">
                    TZS {Number(product.price || 0).toLocaleString()}
                  </div>
                  {product.stock > 0 && product.stock <= 10 && (
                    <div className="mt-1">
                      <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
                        <div 
                          className={`h-full transition-all ${product.stock <= 3 ? 'bg-red-500' : product.stock <= 5 ? 'bg-yellow-500' : 'bg-green-500'}`}
                          style={{ width: `${Math.min(product.stock * 10, 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white">
        <div className="container mx-auto px-4 py-12">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-8">
            {/* Brand */}
            <div className="col-span-2 md:col-span-1">
              <h1 className="text-2xl font-bold text-orange-500 mb-4">Neatify</h1>
              <p className="text-gray-400 text-sm mb-4">Your one-stop shop for all cleaning supplies and tools. Quality products, great prices.</p>
              
              {/* Contact Info */}
              <div className="space-y-2 mb-4">
                <div className="flex items-center space-x-2 text-gray-400 text-sm">
                  <Phone size={16} className="text-orange-500" />
                  <div className="flex gap-2">
                    <a href="tel:0719883695" className="hover:text-orange-400 transition">0719 883 695</a>
                    <span>|</span>
                    <a href="tel:0685395844" className="hover:text-orange-400 transition">0685 395 844</a>
                  </div>
                </div>
                <div className="flex items-center space-x-2 text-gray-400 text-sm">
                  <MapPin size={16} className="text-orange-500" />
                  <span>BIASHARA COMPLEX, Komakoma</span>
                </div>
              </div>
              
              <div className="flex space-x-4">
                <a href="#" className="text-gray-400 hover:text-orange-400 transition">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M24 4.557c-.883.392-1.832.656-2.828.775 1.017-.609 1.798-1.574 2.165-2.724-.951.564-2.005.974-3.127 1.195-.897-.957-2.178-1.555-3.594-1.555-3.179 0-5.515 2.966-4.797 6.045-4.091-.205-7.719-2.165-10.148-5.144-1.29 2.213-.669 5.108 1.523 6.574-.806-.026-1.566-.247-2.229-.616-.054 2.281 1.581 4.415 3.949 4.89-.693.188-1.452.232-2.224.084.626 1.956 2.444 3.379 4.6 3.419-2.07 1.623-4.678 2.348-7.29 2.04 2.179 1.397 4.768 2.212 7.548 2.212 9.142 0 14.307-7.721 13.995-14.646.962-.695 1.797-1.562 2.457-2.549z"/></svg>
                </a>
                <a href="#" className="text-gray-400 hover:text-orange-400 transition">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M22.46 6c-.85.38-1.78.64-2.75.76 1-.6 1.76-1.55 2.12-2.68-.93.55-1.96.95-3.06 1.17-.88-.94-2.13-1.53-3.51-1.53-2.66 0-4.81 2.16-4.81 4.81 0 .38.04.75.13 1.1-4-.2-7.58-2.11-9.96-5.02-.42.72-.66 1.56-.66 2.46 0 1.68.85 3.16 2.14 4.02-.79-.02-1.53-.24-2.18-.6v.06c0 2.35 1.67 4.31 3.88 4.76-.4.1-.83.16-1.27.16-.31 0-.62-.03-.92-.08.63 1.96 2.45 3.39 4.61 3.43-1.69 1.32-3.83 2.1-6.15 2.1-.4 0-.8-.02-1.19-.07 2.19 1.4 4.78 2.22 7.57 2.22 9.07 0 14.02-7.52 14.02-14.02 0-.21 0-.43-.01-.64.96-.7 1.8-1.56 2.46-2.55z"/></svg>
                </a>
                <a href="#" className="text-gray-400 hover:text-orange-400 transition">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>
                </a>
              </div>
            </div>
            <div>
              <h3 className="font-bold mb-4">Get to Know Us</h3>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#" className="hover:text-orange-400 transition">About Us</a></li>
                <li><a href="#" className="hover:text-orange-400 transition">Careers</a></li>
                <li><a href="#" className="hover:text-orange-400 transition">Press Releases</a></li>
                <li><a href="#" className="hover:text-orange-400 transition">Blog</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-bold mb-4">Shop Categories</h3>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#" className="hover:text-orange-400 transition">Electronics</a></li>
                <li><a href="#" className="hover:text-orange-400 transition">Fashion</a></li>
                <li><a href="#" className="hover:text-orange-400 transition">Home & Living</a></li>
                <li><a href="#" className="hover:text-orange-400 transition">Sports</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-bold mb-4">Payment</h3>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#" className="hover:text-orange-400 transition">Business Card</a></li>
                <li><a href="#" className="hover:text-orange-400 transition">Shop with Points</a></li>
                <li><a href="#" className="hover:text-orange-400 transition">Reload Balance</a></li>
                <li><a href="#" className="hover:text-orange-400 transition">Gift Cards</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-bold mb-4">Help</h3>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#" className="hover:text-orange-400 transition">Your Account</a></li>
                <li><a href="#" className="hover:text-orange-400 transition">Your Orders</a></li>
                <li><a href="#" className="hover:text-orange-400 transition">Shipping & Delivery</a></li>
                <li><a href="#" className="hover:text-orange-400 transition">Returns</a></li>
                <li><a href="#" className="hover:text-orange-400 transition">Contact Us</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-10 pt-8">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <p className="text-sm text-gray-400">&copy; 2026 Neatify. All rights reserved.</p>
              <div className="flex items-center gap-6 text-sm text-gray-400">
                <a href="#" className="hover:text-orange-400 transition">Privacy Policy</a>
                <a href="#" className="hover:text-orange-400 transition">Terms of Service</a>
                <a href="#" className="hover:text-orange-400 transition">Cookie Settings</a>
              </div>
            </div>
          </div>
        </div>
      </footer>

      {/* Floating Cart Button */}
      <button
        onClick={() => navigate('/cart')}
        className="fixed bottom-6 right-6 bg-orange-500 text-white p-4 rounded-full shadow-2xl hover:bg-orange-600 transition-all hover:scale-110 z-50"
      >
        <ShoppingCart size={24} />
      </button>
    </div>
  );
};

export default Homepage;