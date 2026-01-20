import { createElement } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import SiteShell from '../components/layout/SiteShell'

import HomePage from '../pages/HomePage'
import ProductsPage from '../pages/ProductsPage'
import ProductDetailPage from '../pages/ProductDetailPage'
import CartPage from '../pages/CartPage'
import CheckoutPage from '../pages/CheckoutPage'
import OrderConfirmationPage from '../pages/OrderConfirmationPage'
import AboutPage from '../pages/AboutPage'
import ContactPage from '../pages/ContactPage'
import PoliciesPage from '../pages/PoliciesPage'

import AdminLayout from '../pages/admin/AdminLayout'
import AdminDashboardPage from '../pages/admin/AdminDashboardPage'
import ProductsAdminPage from '../pages/admin/ProductsAdminPage'
import OrdersAdminPage from '../pages/admin/OrdersAdminPage'
import CustomersAdminPage from '../pages/admin/CustomersAdminPage'
import InventoryAdminPage from '../pages/admin/InventoryAdminPage'

export default function AppRouter() {
  return (
    <Routes>
      <Route element={<SiteShell />}> 
        <Route path="/" element={createElement(HomePage)} />
        <Route path="/products" element={createElement(ProductsPage)} />
        <Route path="/products/:id" element={createElement(ProductDetailPage)} />
        <Route path="/cart" element={createElement(CartPage)} />
        <Route path="/checkout" element={createElement(CheckoutPage)} />
        <Route path="/order/:id" element={createElement(OrderConfirmationPage)} />
        <Route path="/about" element={createElement(AboutPage)} />
        <Route path="/contact" element={createElement(ContactPage)} />
        <Route path="/policies" element={createElement(PoliciesPage)} />

        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboardPage />} />
          <Route path="products" element={<ProductsAdminPage />} />
          <Route path="orders" element={<OrdersAdminPage />} />
          <Route path="customers" element={<CustomersAdminPage />} />
          <Route path="inventory" element={<InventoryAdminPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
