# 10–15 Minute Live Demo Walkthrough Script

Follow this scripted sequence to showcase every requirement in the case study checklist.

---

## Preparation (Before Demo)

```bash
cd food-delivery-microservices
python migrate_all.py      # Apply Alembic migrations to all 8 databases
python seed_all.py         # Seed demo users, restaurants, menus, and addresses
python start_all.py        # Launch all 8 microservices (8001-8008) + API Gateway (8000)

# In a second terminal:
cd food-delivery-microservices/frontend
npm run dev                # Start React SPA on http://localhost:5173
```

---

## Step-by-Step Demo Flow (12–15 Minutes)

### 1. Architecture & Aggregated Health (1.5 min)
- Open `http://127.0.0.1:8000/health` in the browser.
- Highlight all **8 healthy microservices** (`auth-service`, `user-service`, `restaurant-service`, `menu-service`, `order-service`, `delivery-service`, `rating-service`, `report-service`) each connected to its own isolated database.
- Open Swagger UI (`http://127.0.0.1:8008/docs`, `8002/docs`, `8003/docs`) to show OpenAPI schemas and bearer auth.

### 2. Security, Login & Validation (2 min)
- Open `http://localhost:5173/login`.
- Submit empty/invalid credentials -> demonstrate **client-side field-level validation**.
- Submit wrong password -> demonstrate **401 Unauthorized** structured JSON error (and login audit row recorded in `auth_db`).
- Attempt visiting `/reports` directly while logged out -> redirected to `/login` (**ProtectedRoute**).
- Sign in as **Customer 1** (`customer1@fooddelivery.com` / `Customer@123`).
- Try visiting `/reports` as Customer -> **403 Access Denied** enforced in both React and FastAPI.

### 3. Discovery, Search, Filtering, Sorting & Pagination (2 min)
- Navigate to `/restaurants`.
- Demonstrate live search by name, filter by city/cuisine, column sorting (`▲/▼`), and pagination controls.
- Click **Spice Junction** -> view grouped menu served by `menu-service` (`X-Served-By: menu-service`).

### 4. Customer Address CRUD & Order Placement with Pricing Integrity (2.5 min)
- Navigate to `/addresses` -> show pincode validation (`000000` rejected), add a valid address, set default, and demonstrate the **Delete Confirmation Modal**.
- Go back to **Spice Junction**, add items to cart, select delivery address, and click **Place Order**.
- Open the created Order Detail page -> highlight **server-side pricing** (5% tax + free delivery above INR 500, else INR 40) and **immutable item snapshots**.

### 5. End-to-End Multi-Role Business Workflow (4 min)
- **Restaurant Owner** (`owner1@fooddelivery.com` / `Owner@123`):
  - Open `/menu` -> create/toggle availability/soft-delete an item (show ownership guard).
  - Open `/orders` -> transition order `PLACED -> CONFIRMED -> PREPARING -> READY_FOR_PICKUP`.
  - Demonstrate that skipping a state (e.g., `PLACED -> READY_FOR_PICKUP` in Swagger/API) returns **HTTP 409 Conflict**.
- **Admin** (`admin@fooddelivery.com` / `Admin@123`):
  - Open `/orders` -> lookup Order ID -> **Assign Delivery Agent** (`agent_id: 4`).
- **Delivery Agent** (`agent1@fooddelivery.com` / `Agent@123`):
  - Open `/orders` -> view Order Detail **before pickup** (show customer phone is **privacy-masked**).
  - Click `PICKED_UP` -> refresh detail (customer phone is now visible).
  - Click `DELIVERED` -> order timestamped as delivered.
- **Customer 1**:
  - Open delivered Order Detail -> submit Restaurant & Agent **Rating** (`rating-service` recomputes and updates `avg_rating` in `restaurant-service`).
- **Admin**:
  - Open `/reports` -> view **Sales Summary**, **Delivery Agent Performance** (with average rating), and **Platform Cancellation Rate** aggregated across 4 microservices.

### 6. Automated Tests & Coverage Evidence (2 min)
```bash
# Backend pytest + coverage (>= 70% target)
python -m pytest -v --cov=services --cov=api-gateway

# Frontend Vitest + React Testing Library
cd frontend && npm test
```
