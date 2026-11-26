# Food Delivery Order Management System — Full-Stack Microservices Platform

## 1. Problem Statement

Modern food delivery platforms serve four distinct personas—**Customers**, **Restaurant Owners**, **Delivery Agents**, and **Platform Administrators**—with strict requirements around pricing integrity, deterministic order lifecycle transitions, participant-only data privacy, and independent scalability. This solution provides a **separate React SPA frontend** and an **8-microservice + API Gateway FastAPI backend**, each with its **own isolated relational database** (SQLite for local zero-config runs, plus full **MySQL 8.0** and **PostgreSQL 16** Docker Compose setups) and independent **Alembic migrations**.

> The original monolithic application archive was kept completely untouched.

---

## 2. Architecture Overview

Detailed Mermaid **Component Architecture**, **ER Diagram**, and **Order State Machine** diagrams are available in [docs/Architecture_and_ER_Diagrams.md](docs/Architecture_and_ER_Diagrams.md).

| Component / Service | Port | Dedicated Database | Owned Tables | Responsibility |
|---|---:|---|---|---|
| **frontend (React + Vite)** | `5173` | — | — | Responsive SPA with React Router, role-protected navigation, validated forms, searchable/sortable tables |
| **api-gateway** | `8000` | *(Stateless)* | — | Unified `/api/v1/*` reverse proxy, `/health` aggregator, blocks `/internal/*` |
| **auth-service** | `8008` | `auth_db` (`auth_service.db`) | `auth_credentials`, `login_audit_logs` | Registration, Login (JSON & OAuth2 form), bcrypt hashing, JWT issuance, Admin onboarding, login audit |
| **user-service** | `8001` | `user_db` (`user_service.db`) | `users`, `addresses` | User profiles (no password hashes), customer profile updates & delivery addresses |
| **restaurant-service** | `8002` | `restaurant_db` (`restaurant_service.db`) | `restaurants` | Restaurant CRUD, open/closed toggle, search with pagination, average rating storage |
| **menu-service** | `8007` | `menu_db` (`menu_service.db`) | `menu_categories`, `menu_items` | Menu categories CRUD, menu items CRUD, soft-delete, availability toggle, grouped restaurant menu |
| **order-service** | `8003` | `order_db` (`order_service.db`) | `orders`, `order_items`, `order_status_history` | Order placement with server-side pricing snapshots, state machine, participant-only IDOR & phone masking |
| **delivery-service** | `8004` | `delivery_db` (`delivery_service.db`) | `deliveries`, `delivery_events` | Admin agent assignment, agent assigned-orders listing, `PICKED_UP` / `DELIVERED` lifecycle |
| **rating-service** | `8005` | `rating_db` (`rating_service.db`) | `ratings` | Post-delivery ratings, average rating recomputation pushed to `restaurant-service` |
| **report-service** | `8006` | `report_db` (`report_service.db`) | `report_snapshots` | Restaurant sales, delivery agent performance, cancellation/rejection rate reports |

### Layered Folder Structure per Microservice

Every microservice under `services/<service-name>/` follows the same clean modular layout:

```text
services/<service-name>/
├── alembic/               # Alembic environment & versioned migrations
│   └── versions/001_initial_schema.py
├── alembic.ini
├── app/
│   ├── core/              # Pydantic Settings, constants, DB session/engine, pagination, state machine
│   ├── security/          # JWT auth, bcrypt hashing (auth-service), RBAC dependencies, IDOR permissions, internal API key
│   ├── exceptions/        # Custom AppException hierarchy (400-503) & global FastAPI handlers
│   ├── models/            # Service-owned SQLAlchemy ORM models (zero cross-DB FKs)
│   ├── schemas/           # Pydantic v2 request/response schemas with field constraints
│   ├── repositories/      # Pure database access layer scoped to this service's DB
│   ├── services/          # Pure business logic & domain orchestration
│   ├── clients/           # Inter-service HTTP clients (httpx + X-Internal-API-Key)
│   ├── routers/           # Public /api/v1/*, /internal/*, and /health endpoints
│   ├── utils/             # Service utilities (Decimal pricing, order number generator)
│   └── main.py            # FastAPI entrypoint, CORS, lifespan setup
├── .env.example
├── Dockerfile
├── requirements.txt
└── run.py
```

---

## 3. Prerequisites

- **Python 3.11+** (tested on Python 3.14)
- **Node.js 20+** and **npm 10+** (for the React frontend)
- **Docker & Docker Compose** *(optional, for running with 8 MySQL 8.0 or PostgreSQL 16 databases)*

---

## 4. Environment Configuration

Copy the environment templates before running in custom/production environments (never commit real `.env` files):

- Root template: [`.env.example`](.env.example)
- Per-service templates: `services/<service-name>/.env.example` and `api-gateway/.env.example`
- Frontend template: [`frontend/.env.example`](frontend/.env.example) (`VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1`)

---

## 5. Local Setup, Migrations, Seeding & Startup

### Backend (8 Microservices + API Gateway)
```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Run Alembic migrations across all 8 microservice databases
python migrate_all.py

# 3. Seed demo users, restaurants, menu categories/items, and addresses
python seed_all.py

# 4. Launch all 8 microservices (ports 8001-8008) + API Gateway (port 8000)
python start_all.py
```

### Frontend (Separate React + Vite Application)
```bash
cd frontend
npm install
npm run dev
```

### Docker Compose (MySQL 8.0 or PostgreSQL 16)
```bash
# 8 separate MySQL 8.0 databases + 8 microservices + API Gateway:
docker compose -f docker-compose.mysql.yml up --build

# Or 8 separate PostgreSQL 16 databases + 8 microservices + API Gateway:
docker compose up --build
```

---

## 6. API & UI URLs

- **React Frontend:** `http://localhost:5173`
- **API Gateway Base URL:** `http://127.0.0.1:8000/api/v1`
- **Aggregated Health Check:** `http://127.0.0.1:8000/health`
- **Swagger / OpenAPI Docs (per microservice):**
  - Auth Service: `http://127.0.0.1:8008/docs`
  - User Service: `http://127.0.0.1:8001/docs`
  - Restaurant Service: `http://127.0.0.1:8002/docs`
  - Menu Service: `http://127.0.0.1:8007/docs`
  - Order Service: `http://127.0.0.1:8003/docs`
  - Delivery Service: `http://127.0.0.1:8004/docs`
  - Rating Service: `http://127.0.0.1:8005/docs`
  - Report Service: `http://127.0.0.1:8006/docs`

---

## 7. Seeded Demo Credentials

| Role | Email | Password |
|---|---|---|
| `ADMIN` | `admin@fooddelivery.com` | `Admin@123` |
| `RESTAURANT_OWNER` | `owner1@fooddelivery.com` | `Owner@123` |
| `RESTAURANT_OWNER` | `owner2@fooddelivery.com` | `Owner@123` |
| `DELIVERY_AGENT` | `agent1@fooddelivery.com` | `Agent@123` |
| `DELIVERY_AGENT` | `agent2@fooddelivery.com` | `Agent@123` |
| `CUSTOMER` | `customer1@fooddelivery.com` | `Customer@123` |
| `CUSTOMER` | `customer2@fooddelivery.com` | `Customer@123` |

---

## 8. Running Tests & Linting

```bash
# Backend automated tests with coverage (90% total coverage across 8 services + gateway)
python -m pytest -v --cov=services --cov=api-gateway --cov-report=term

# Frontend tests (Vitest + React Testing Library), ESLint, and production build
cd frontend
npm test
npm run lint
npm run build
```

---

## 9. Additional Documentation

- **Architecture, ER & State Machine Diagrams:** [docs/Architecture_and_ER_Diagrams.md](docs/Architecture_and_ER_Diagrams.md)
- **Test Results & Coverage Evidence:** [docs/Test_Results.md](docs/Test_Results.md)
- **10–15 Minute Live Demo Script:** [docs/Demo_Script.md](docs/Demo_Script.md)
- **Design Decisions, Trade-offs & Limitations:** [docs/Design_Decisions_and_Limitations.md](docs/Design_Decisions_and_Limitations.md)
