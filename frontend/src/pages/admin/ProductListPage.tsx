/**
 * ProductListPage - Enhanced product management with DataTable
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import {
  Plus,
  Package,
  Edit2,
  Trash2,
  Copy,
  Eye,
  MoreHorizontal,
  Download,
  Upload,
  AlertTriangle,
  Search,
  X,
} from 'lucide-react';
import { useAdminStore } from '@/stores/adminStore';
import { DataTable, Column } from '@/components/admin/DataTable';
import { ConfirmDialog } from '@/components/admin/ConfirmDialog';
import { formatCurrency } from '@/services/adminService';
import { getImageUrl } from '@/app/api';

interface Product {
  id: number;
  name: string;
  sku: string;
  category_id: number;
  category_name?: string;
  price: number;
  compare_at_price?: number;
  stock: number;
  is_active: boolean;
  is_featured: boolean;
  primary_image?: string;
  created_at: string;
}

export default function ProductListPage() {
  const navigate = useNavigate();
  const {
    products,
    categories,
    fetchProducts,
    fetchCategories,
    deleteProduct,
    showToast,
  } = useAdminStore();

  const [selectedProducts, setSelectedProducts] = useState<number[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<{
    open: boolean;
    product?: Product;
    bulk?: boolean;
  }>({ open: false });
  const [actionMenu, setActionMenu] = useState<number | null>(null);

  useEffect(() => {
    fetchProducts();
    fetchCategories();
  }, [fetchProducts, fetchCategories]);

  // Search handler
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchProducts({ search: searchQuery, page: 1 });
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    fetchProducts({ page: 1 });
  };

  const handlePageChange = (page: number) => {
    fetchProducts({ page });
  };

  const handleCategoryChange = (value: string) => {
    setCategoryFilter(value);
    fetchProducts({ category_id: value ? parseInt(value) : undefined, page: 1 });
  };

  const handleStatusChange = (value: string) => {
    setStatusFilter(value);
    let filters: Record<string, unknown> = { page: 1 };
    if (value === 'active') filters.is_active = true;
    else if (value === 'inactive') filters.is_active = false;
    else if (value === 'featured') filters.is_featured = true;
    else if (value === 'low_stock') filters.low_stock = true;
    fetchProducts(filters);
  };

  // Actions
  const handleDeleteClick = (product: Product) => {
    setDeleteConfirm({ open: true, product });
    setActionMenu(null);
  };

  const handleBulkDeleteClick = () => {
    if (selectedProducts.length === 0) return;
    setDeleteConfirm({ open: true, bulk: true });
  };

  const handleDeleteConfirm = async () => {
    if (deleteConfirm.bulk) {
      // Bulk delete
      const promises = selectedProducts.map((id) => deleteProduct(id));
      const results = await Promise.allSettled(promises);
      const failed = results.filter((r) => r.status === 'rejected').length;
      if (failed > 0) {
        showToast(`Failed to delete ${failed} products`, 'error');
      } else {
        showToast(`${selectedProducts.length} products deleted`, 'success');
      }
      setSelectedProducts([]);
    } else if (deleteConfirm.product) {
      try {
        await deleteProduct(deleteConfirm.product.id);
        showToast('Product deleted successfully', 'success');
      } catch {
        showToast('Failed to delete product', 'error');
      }
    }
    setDeleteConfirm({ open: false });
  };

  const handleDuplicateProduct = (product: Product) => {
    navigate(`/admin/products/new?duplicate=${product.id}`);
    setActionMenu(null);
  };

  const handleSelectionChange = (ids: (string | number)[]) => {
    setSelectedProducts(ids.map((id) => Number(id)));
  };

  // Table columns
  const columns: Column<Product>[] = [
    {
      key: 'name',
      header: 'Product',
      sortable: true,
      render: (_: unknown, row: Product) => (
        <div className="flex items-center gap-3">
          {row.primary_image ? (
            <img
              src={getImageUrl(row.primary_image)}
              alt={row.name}
              className="h-10 w-10 rounded-lg object-cover"
              crossOrigin="anonymous"
              onError={(e) => {
                e.currentTarget.src = getImageUrl(null);
                e.currentTarget.onerror = null;
              }}
            />
          ) : (
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-700">
              <Package className="h-5 w-5 text-gray-500 dark:text-slate-400" />
            </div>
          )}
          <div className="min-w-0">
            <p className="truncate font-medium text-gray-900 dark:text-white">{row.name}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">SKU: {row.sku}</p>
          </div>
        </div>
      ),
    },
    {
      key: 'category_name',
      header: 'Category',
      sortable: true,
      render: (value) => (
        <span className="text-slate-300">{value || 'Uncategorized'}</span>
      ),
    },
    {
      key: 'price',
      header: 'Price',
      sortable: true,
      align: 'right',
      render: (value, row) => (
        <div className="text-right">
          <p className="font-medium text-gray-900 dark:text-white">{formatCurrency(value)}</p>
          {row.compare_at_price && row.compare_at_price > value && (
            <p className="text-xs text-slate-500 line-through">
              {formatCurrency(row.compare_at_price)}
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'stock',
      header: 'Stock',
      sortable: true,
      align: 'center',
      render: (value) => (
        <span
          className={clsx(
            'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
            value === 0
              ? 'bg-red-500/10 text-red-400'
              : value < 10
                ? 'bg-amber-500/10 text-amber-400'
                : 'bg-emerald-500/10 text-emerald-400'
          )}
        >
          {value === 0 ? <AlertTriangle className="h-3 w-3" /> : null}
          {value}
        </span>
      ),
    },
    {
      key: 'is_active',
      header: 'Status',
      align: 'center',
      render: (value, row) => (
        <div className="flex flex-col items-center gap-1">
          <span
            className={clsx(
              'rounded-full px-2 py-0.5 text-xs font-medium',
              value ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-500/10 text-gray-500 dark:text-slate-400'
            )}
          >
            {value ? 'Active' : 'Inactive'}
          </span>
          {row.is_featured && (
            <span className="rounded-full bg-purple-500/10 px-2 py-0.5 text-xs font-medium text-purple-400">
              Featured
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (_, row) => (
        <div className="relative">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setActionMenu(actionMenu === row.id ? null : row.id);
            }}
            className="rounded p-1 text-gray-500 dark:text-slate-400 hover:bg-slate-700 hover:text-gray-900 dark:text-white"
            aria-label="Product actions"
          >
            <MoreHorizontal className="h-5 w-5" />
          </button>

          {actionMenu === row.id && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setActionMenu(null)}
              />
              <div className="absolute right-0 top-8 z-20 w-48 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 py-1 shadow-lg">
                <Link
                  to={`/products/${row.id}`}
                  target="_blank"
                  className="flex w-full items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700"
                >
                  <Eye className="h-4 w-4" />
                  View in Store
                </Link>
                <Link
                  to={`/admin/products/${row.id}`}
                  className="flex w-full items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700"
                >
                  <Edit2 className="h-4 w-4" />
                  Edit
                </Link>
                <button
                  onClick={() => handleDuplicateProduct(row)}
                  className="flex w-full items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700"
                >
                  <Copy className="h-4 w-4" />
                  Duplicate
                </button>
                <div className="my-1 border-t border-gray-200 dark:border-slate-700" />
                <button
                  onClick={() => handleDeleteClick(row)}
                  className="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-slate-700"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete
                </button>
              </div>
            </>
          )}
        </div>
      ),
    },
  ];

  // Bulk actions
  const bulkActions = (
    <>
      {selectedProducts.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500 dark:text-slate-400">
            {selectedProducts.length} selected
          </span>
          <button
            onClick={handleBulkDeleteClick}
            className="flex items-center gap-1 rounded-lg bg-red-500/10 px-3 py-1.5 text-sm font-medium text-red-400 hover:bg-red-500/20"
          >
            <Trash2 className="h-4 w-4" />
            Delete
          </button>
        </div>
      )}
    </>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Products</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400">
            Manage your product catalog ({products.total} products)
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700">
            <Upload className="h-4 w-4" />
            Import
          </button>
          <button className="flex items-center gap-2 rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700">
            <Download className="h-4 w-4" />
            Export
          </button>
          <Link
            to="/admin/products/new"
            className="flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-gray-900 dark:text-white hover:bg-emerald-600"
          >
            <Plus className="h-4 w-4" />
            Add Product
          </Link>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Search */}
        <form onSubmit={handleSearch} className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500 dark:text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search products by name, SKU..."
            className="w-full rounded-lg border border-slate-600 bg-white dark:bg-slate-800 py-2 pl-10 pr-10 text-sm text-gray-900 dark:text-white placeholder:text-gray-500 dark:text-slate-400 focus:border-emerald-500 focus:outline-none"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={handleClearSearch}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:text-white"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </form>

        {/* Category Filter */}
        <select
          value={categoryFilter}
          onChange={(e) => handleCategoryChange(e.target.value)}
          className="rounded-lg border border-slate-600 bg-white dark:bg-slate-800 px-4 py-2 text-sm text-gray-900 dark:text-white focus:border-emerald-500 focus:outline-none"
          aria-label="Filter by category"
        >
          <option value="">All Categories</option>
          {categories.items.map((cat) => (
            <option key={cat.id} value={cat.id}>
              {cat.name}
            </option>
          ))}
        </select>

        {/* Status Filter */}
        <select
          value={statusFilter}
          onChange={(e) => handleStatusChange(e.target.value)}
          className="rounded-lg border border-slate-600 bg-white dark:bg-slate-800 px-4 py-2 text-sm text-gray-900 dark:text-white focus:border-emerald-500 focus:outline-none"
          aria-label="Filter by status"
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="featured">Featured</option>
          <option value="low_stock">Low Stock</option>
          <option value="out_of_stock">Out of Stock</option>
        </select>
      </div>

      {/* Bulk Actions */}
      {bulkActions}

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={products.items as unknown as Product[]}
        isLoading={products.isLoading}
        page={products.page}
        pageSize={products.pageSize}
        total={products.total}
        totalPages={products.totalPages}
        onPageChange={handlePageChange}
        selectable
        selectedIds={selectedProducts}
        onSelectionChange={handleSelectionChange}
        onRowClick={(row: Product) => navigate(`/admin/products/${row.id}`)}
        emptyMessage="No products found. Get started by adding your first product."
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteConfirm.open}
        onClose={() => setDeleteConfirm({ open: false })}
        onConfirm={handleDeleteConfirm}
        title={deleteConfirm.bulk ? 'Delete Products' : 'Delete Product'}
        message={
          deleteConfirm.bulk
            ? `Are you sure you want to delete ${selectedProducts.length} products? This action cannot be undone.`
            : `Are you sure you want to delete "${deleteConfirm.product?.name}"? This action cannot be undone.`
        }
        variant="danger"
        confirmLabel="Delete"
      />
    </div>
  );
}
