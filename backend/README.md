# E-Commerce & Store (React + FastAPI + PostgreSQL)

A clean, scalable foundation for a Shopify-style online store:

- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Backend:** Python + FastAPI
- **Database:** PostgreSQL via SQLAlchemy

This repo includes:
- Public storefront pages (home, products, product detail, cart, checkout, order confirmation)
- Admin panel pages (dashboard, products, orders, customers, inventory)
- Core backend services (products, customers, orders, payments, inventory logs)

---

## Project Structure

```
e_commerce&store/
  backend/
    app/
  frontend/
```

---

## Backend (FastAPI)

### 1) Create virtualenv + install deps

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r e_commerce&store/backend/requirements.txt
```

### 2) Configure environment

Set environment variables (optional; sensible defaults exist for local dev):

```bash
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/ecommerce"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="admin123"
export JWT_SECRET="change-me"
export CORS_ORIGINS="http://localhost:5173"
```

> If `DATABASE_URL` is not set, the backend falls back to a local SQLite database (`./app.db`) for quick start.

### 3) Run API

```bash
uvicorn e_commerce&store.backend.app.main:app --reload --port 8000
```

### 4) Seed sample data

```bash
python -m e_commerce\&store.backend.app.seed
```

API base URL:
- `http://localhost:8000/api`
- Swagger: `http://localhost:8000/docs`

---

## Frontend (React)

### 1) Install

```bash
pnpm --dir e_commerce\&store/frontend install
```

### 2) Run

```bash
pnpm --dir e_commerce\&store/frontend dev
```

Frontend URL:
- `http://localhost:5173`

---

## Notes / Defaults

- **Payments** are implemented as a simple "mock" payment verification endpoint to keep the foundation clean.
- **Admin auth** uses JWT with a single username/password from environment variables.
- Inventory reductions happen automatically when an order is created.

---

## Next Enhancements

- Real payment gateway integration (Stripe/Razorpay)
- Email notifications (SendGrid/SES)
- Role-based access (admin/staff)
- Shipping provider integration + tracking
- Analytics dashboards (daily/monthly sales, best sellers)