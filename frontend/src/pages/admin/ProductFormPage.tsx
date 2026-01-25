/**
 * ProductFormPage - Simplified Create/Edit product with image upload
 * Fields: Product Name, Category (optional), Image, Price, New Price (for discounts)
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import clsx from 'clsx';
import {
  ArrowLeft,
  Save,
  Package,
  DollarSign,
  Image as ImageIcon,
  AlertCircle,
  Loader2,
  Upload,
  X,
  Plus,
  FolderPlus,
} from 'lucide-react';
import { useAdminStore } from '@/stores/adminStore';
import { useToast } from '@/components/admin/Toast';
import { adminService } from '@/services/adminService';
import { getImageUrl, adminCategoriesAPI } from '@/app/api';

interface ProductFormData {
  name: string;
  category_id: string;
  price: string;
  new_price: string;
}

const initialFormData: ProductFormData = {
  name: '',
  category_id: '',
  price: '',
  new_price: '',
};

export default function ProductFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { categories, fetchCategories } = useAdminStore();

  const isEdit = Boolean(id);

  // Multi-image state
  const [selectedImages, setSelectedImages] = useState<File[]>([]);
  const [existingImages, setExistingImages] = useState<Array<{ id: number; url: string; is_primary: boolean }>>([]);
  const [deletedImageIds, setDeletedImageIds] = useState<number[]>([]);

  const [formData, setFormData] = useState<ProductFormData>(initialFormData);
  const [errors, setErrors] = useState<Partial<Record<keyof ProductFormData, string>>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isFetching, setIsFetching] = useState(false);

  // Category creation modal state
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newCategoryDescription, setNewCategoryDescription] = useState('');
  const [isCreatingCategory, setIsCreatingCategory] = useState(false);
  const [categoryError, setCategoryError] = useState('');

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  // Fetch product data for edit
  useEffect(() => {
    if (id) {
      setIsFetching(true);
      adminService.productsAPI
        .getById(Number(id))
        .then((product) => {
          setFormData({
            name: product.name || '',
            category_id: product.category?.id?.toString() || '',
            price: product.original_price?.toString() || product.price?.toString() || '',
            new_price: product.price?.toString() || '',
          });

          // Load existing images
          if (product.images && product.images.length > 0) {
            setExistingImages(product.images.map(img => ({
              id: img.id,
              url: img.url,
              is_primary: img.is_primary
            })));
          } else if (product.primary_image) {
            // Fallback for older data structure if needed, though interface suggests images array
            // Ideally we refetch or trust the images array. 
            // If products endpoint didn't return images array populated, we might need a separate fetch?
            // But adminService.productsAPI.getById returns AdminProduct which has images array.
          }
        })
        .catch(() => {
          showToast('Failed to load product', 'error');
          navigate('/admin/products');
        })
        .finally(() => {
          setIsFetching(false);
        });
    }
  }, [id, navigate, showToast]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    // Clear error on change
    if (errors[name as keyof ProductFormData]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const newFiles = Array.from(files);
      const validFiles = newFiles.filter(file => {
        if (file.size > 5 * 1024 * 1024) {
          showToast(`Skipped ${file.name}: File too large (max 5MB)`, 'error');
          return false;
        }
        return true;
      });

      setSelectedImages(prev => [...prev, ...validFiles]);
    }

    // Reset input
    e.target.value = '';
  };

  const removeSelectedImage = (index: number) => {
    setSelectedImages(prev => prev.filter((_, i) => i !== index));
  };

  const removeExistingImage = (imageId: number) => {
    setExistingImages(prev => prev.filter(img => img.id !== imageId));
    setDeletedImageIds(prev => [...prev, imageId]);
  };

  // Handle creating a new category
  const handleCreateCategory = async () => {
    if (!newCategoryName.trim()) {
      setCategoryError('Category name is required');
      return;
    }

    setIsCreatingCategory(true);
    setCategoryError('');

    try {
      const response = await adminCategoriesAPI.create({
        name: newCategoryName.trim(),
        description: newCategoryDescription.trim() || undefined,
      });

      // Refresh categories list
      await fetchCategories();

      // Auto-select the new category
      const newCatId = response.data?.id;
      if (newCatId) {
        setFormData((prev) => ({ ...prev, category_id: newCatId.toString() }));
      }

      // Reset and close modal
      setNewCategoryName('');
      setNewCategoryDescription('');
      setShowCategoryModal(false);
      showToast('Category created successfully!', 'success');
    } catch (error: any) {
      const message = error?.response?.data?.detail || 'Failed to create category';
      setCategoryError(message);
    } finally {
      setIsCreatingCategory(false);
    }
  };

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof ProductFormData, string>> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Product name is required';
    }
    if (!formData.price || parseFloat(formData.price) <= 0) {
      newErrors.price = 'Valid price is required';
    }
    if (formData.new_price && parseFloat(formData.new_price) <= 0) {
      newErrors.new_price = 'New price must be greater than 0';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      showToast('Please fix the form errors', 'error');
      return;
    }

    setIsLoading(true);

    try {
      let savedProduct;

      // 1. Save Product Details
      if (isEdit) {
        const productData = {
          name: formData.name,
          category_ids: formData.category_id ? [parseInt(formData.category_id)] : [],
          price: parseFloat(formData.price),
          original_price: parseFloat(formData.price),
          sale_price: formData.new_price ? parseFloat(formData.new_price) : undefined,
        };
        savedProduct = await adminService.productsAPI.update(Number(id), productData);
      } else {
        const productData = {
          name: formData.name,
          category_id: formData.category_id ? parseInt(formData.category_id) : null,
          price: parseFloat(formData.price),
          new_price: formData.new_price ? parseFloat(formData.new_price) : null,
        };
        savedProduct = await adminService.productsAPI.createSimple(productData);
      }

      const productId = savedProduct.id;

      // 2. Process Deletions
      if (deletedImageIds.length > 0) {
        await Promise.all(deletedImageIds.map(imgId => adminService.productsAPI.deleteImage(imgId)));
      }

      // 3. Process Uploads
      if (selectedImages.length > 0) {
        // First image is primary if there are no existing images, or if specified logic requires it
        // For simplicity, just upload them. The backend handles default primary logic usually,
        // or we can set it explicitly.

        // If no existing images and this is the first of selected, make it primary
        const hasExisting = existingImages.length > 0;

        for (let i = 0; i < selectedImages.length; i++) {
          const isPrimary = !hasExisting && i === 0;
          await adminService.productsAPI.uploadImage(productId, selectedImages[i], isPrimary);
        }
      }

      showToast(`Product ${isEdit ? 'updated' : 'created'} successfully`, 'success');
      navigate('/admin/products');
    } catch (error: unknown) {
      console.error('Save error:', error);
      const message = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to save product';
      showToast(message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  if (isFetching) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/admin/products')}
            className="rounded-lg p-2 text-gray-500 dark:text-slate-400 hover:bg-slate-700 hover:text-gray-900 dark:text-white"
            aria-label="Go back to products"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {isEdit ? 'Edit Product' : 'Add New Product'}
            </h1>
            <p className="text-sm text-gray-500 dark:text-slate-400">
              {isEdit ? 'Update product details' : 'Create a new product'}
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <section className="rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <Package className="h-5 w-5 text-emerald-400" />
            Product Information
          </h2>
          <div className="space-y-4">
            {/* Product Name */}
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">
                Product Name <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                className={clsx(
                  'w-full rounded-lg border bg-slate-900 px-4 py-3 text-gray-900 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2',
                  errors.name
                    ? 'border-red-500 focus:ring-red-500'
                    : 'border-slate-600 focus:border-emerald-500 focus:ring-emerald-500'
                )}
                placeholder="Enter product name"
              />
              {errors.name && (
                <p className="mt-1 flex items-center gap-1 text-sm text-red-400">
                  <AlertCircle className="h-4 w-4" />
                  {errors.name}
                </p>
              )}
            </div>

            {/* Category */}
            <div>
              <label htmlFor="category_id" className="mb-1 block text-sm font-medium text-slate-300">
                Category <span className="text-slate-500">(Optional)</span>
              </label>
              <div className="flex gap-2">
                <select
                  id="category_id"
                  name="category_id"
                  value={formData.category_id}
                  onChange={handleChange}
                  className="flex-1 rounded-lg border border-slate-600 bg-slate-900 px-4 py-3 text-gray-900 dark:text-white focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  aria-label="Product category"
                >
                  <option value="">Select category (optional)</option>
                  {categories.items.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setShowCategoryModal(true)}
                  className="flex items-center gap-2 rounded-lg border border-emerald-500 bg-emerald-500/10 px-4 py-3 text-emerald-400 transition hover:bg-emerald-500/20"
                  title="Add new category"
                >
                  <Plus className="h-5 w-5" />
                  <span className="hidden sm:inline">Add</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Product Images */}
        <section className="rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <ImageIcon className="h-5 w-5 text-emerald-400" />
            Product Images
          </h2>

          <div className="space-y-4">
            {/* Image Grid */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
              {/* Existing Images */}
              {existingImages.map((img) => (
                <div key={img.id} className="relative group aspect-square rounded-lg border border-slate-600 overflow-hidden bg-slate-900">
                  <img
                    src={getImageUrl(img.url)}
                    alt="Product"
                    className="h-full w-full object-cover"
                    crossOrigin="anonymous"
                    onError={(e) => {
                      e.currentTarget.src = getImageUrl(null);
                      e.currentTarget.onerror = null;
                    }}
                  />
                  {img.is_primary && (
                    <span className="absolute left-2 top-2 rounded bg-emerald-500 px-1.5 py-0.5 text-[10px] font-bold text-white shadow-sm">
                      Primary
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => removeExistingImage(img.id)}
                    className="absolute right-2 top-2 rounded-full bg-red-500 p-1.5 text-white opacity-0 transition-opacity group-hover:opacity-100 hover:bg-red-600"
                    title="Remove image"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}

              {/* New Selected Images */}
              {selectedImages.map((file, index) => (
                <div key={`new-${index}`} className="relative group aspect-square rounded-lg border border-dashed border-emerald-500/50 overflow-hidden bg-slate-900/50">
                  <img
                    src={URL.createObjectURL(file)}
                    alt="New upload"
                    className="h-full w-full object-cover opacity-80"
                  />
                  <span className="absolute bottom-2 right-2 rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-bold text-emerald-400 border border-emerald-500/20">
                    New
                  </span>
                  <button
                    type="button"
                    onClick={() => removeSelectedImage(index)}
                    className="absolute right-2 top-2 rounded-full bg-red-500 p-1.5 text-white opacity-0 transition-opacity group-hover:opacity-100 hover:bg-red-600"
                    title="Remove upload"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}

              {/* Upload Button Block */}
              <label className="flex aspect-square cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-600 bg-slate-900/30 transition hover:border-emerald-500 hover:bg-slate-900/50">
                <Upload className="mb-2 h-6 w-6 text-gray-500 dark:text-slate-400" />
                <span className="text-xs font-medium text-slate-300">Add Images</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageSelect}
                  className="hidden"
                  multiple
                />
              </label>
            </div>

            <p className="text-xs text-slate-500">
              * Supports multi-select. First uploaded image will be primary if none exist.
            </p>
          </div>
        </section>

        {/* Pricing */}
        <section className="rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
            <DollarSign className="h-5 w-5 text-emerald-400" />
            Pricing
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {/* Price */}
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">
                Price <span className="text-red-400">*</span>
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 dark:text-slate-400">$</span>
                <input
                  type="number"
                  name="price"
                  value={formData.price}
                  onChange={handleChange}
                  min="0"
                  step="0.01"
                  className={clsx(
                    'w-full rounded-lg border bg-slate-900 pl-8 pr-4 py-3 text-gray-900 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2',
                    errors.price
                      ? 'border-red-500 focus:ring-red-500'
                      : 'border-slate-600 focus:border-emerald-500 focus:ring-emerald-500'
                  )}
                  placeholder="0.00"
                />
              </div>
              {errors.price && (
                <p className="mt-1 flex items-center gap-1 text-sm text-red-400">
                  <AlertCircle className="h-4 w-4" />
                  {errors.price}
                </p>
              )}
            </div>

            {/* New Price (Discount) */}
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">
                New Price <span className="text-slate-500">(Sale/Discount)</span>
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 dark:text-slate-400">$</span>
                <input
                  type="number"
                  name="new_price"
                  value={formData.new_price}
                  onChange={handleChange}
                  min="0"
                  step="0.01"
                  className={clsx(
                    'w-full rounded-lg border bg-slate-900 pl-8 pr-4 py-3 text-gray-900 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2',
                    errors.new_price
                      ? 'border-red-500 focus:ring-red-500'
                      : 'border-slate-600 focus:border-emerald-500 focus:ring-emerald-500'
                  )}
                  placeholder="0.00"
                />
              </div>
              {errors.new_price && (
                <p className="mt-1 flex items-center gap-1 text-sm text-red-400">
                  <AlertCircle className="h-4 w-4" />
                  {errors.new_price}
                </p>
              )}
              <p className="mt-1 text-xs text-slate-500">
                Leave empty if no discount. Original price will be shown crossed out.
              </p>
            </div>
          </div>
        </section>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate('/admin/products')}
            className="rounded-lg border border-slate-600 px-6 py-3 text-sm font-medium text-slate-300 hover:bg-slate-700"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isLoading}
            className="flex items-center gap-2 rounded-lg bg-emerald-500 px-6 py-3 text-sm font-medium text-gray-900 dark:text-white hover:bg-emerald-600 disabled:opacity-50"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {isEdit ? 'Update Product' : 'Create Product'}
          </button>
        </div>
      </form>

      {/* Add Category Modal */}
      {showCategoryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-md rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
                <FolderPlus className="h-5 w-5 text-emerald-400" />
                Add New Category
              </h3>
              <button
                onClick={() => {
                  setShowCategoryModal(false);
                  setNewCategoryName('');
                  setNewCategoryDescription('');
                  setCategoryError('');
                }}
                className="rounded-lg p-1 text-gray-500 dark:text-slate-400 hover:bg-slate-700 hover:text-gray-900 dark:text-white"
                aria-label="Close modal"
                title="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">
                  Category Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={newCategoryName}
                  onChange={(e) => {
                    setNewCategoryName(e.target.value);
                    setCategoryError('');
                  }}
                  className="w-full rounded-lg border border-slate-600 bg-slate-900 px-4 py-3 text-gray-900 dark:text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="e.g., Electronics, Clothing, Home & Garden"
                  autoFocus
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">
                  Description <span className="text-slate-500">(Optional)</span>
                </label>
                <textarea
                  value={newCategoryDescription}
                  onChange={(e) => setNewCategoryDescription(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-slate-600 bg-slate-900 px-4 py-3 text-gray-900 dark:text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="Brief description of this category..."
                />
              </div>

              {categoryError && (
                <p className="flex items-center gap-1 text-sm text-red-400">
                  <AlertCircle className="h-4 w-4" />
                  {categoryError}
                </p>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowCategoryModal(false);
                  setNewCategoryName('');
                  setNewCategoryDescription('');
                  setCategoryError('');
                }}
                className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCreateCategory}
                disabled={isCreatingCategory || !newCategoryName.trim()}
                className="flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-gray-900 dark:text-white hover:bg-emerald-600 disabled:opacity-50"
              >
                {isCreatingCategory ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                Create Category
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
