# Automated Test Results & Coverage Evidence

## 1. Backend Microservices Tests (Pytest + Coverage)

### Command
```bash
python -m pytest -v --cov=services --cov=api-gateway --cov-report=term
```

### Results Summary
- **Result:** `5 passed in 15.83s`
- **Total Statements:** `4,082`
- **Missed Statements:** `405`
- **Total Line Coverage:** **`90%`** (exceeds the `70%` target by 20 percentage points)

### Scenarios Covered
| Test | Coverage Scope |
|---|---|
| `test_01_gateway_health_and_database_per_service_isolation` | Aggregated `/health` across all 8 microservices + SQLite schema inspection proving all 8 databases contain strictly their own domain tables |
| `test_02_internal_endpoints_security_protection` | API Gateway blocks `/internal/*` with `403 INTERNAL_ROUTE_FORBIDDEN`; direct calls without `X-Internal-API-Key` return `401`; valid internal key succeeds |
| `test_03_full_end_to_end_food_delivery_workflow` | OAuth2 form & JSON login (`auth-service`), admin onboarding, duplicate registration (`409`), customer profile & address IDOR (`403`), restaurant/menu CRUD & ownership (`403`), server-side price tampering prevention, state machine (`409` on invalid transition), delivery agent assignment, phone masking before `PICKED_UP`, post-delivery rating syncing `avg_rating`, and aggregated sales/agent/cancellation reports + DB persistence checks (`auth_db`, `delivery_db`, `report_db`) |
| `test_04_auth_security_validation_and_gateway_errors` | Wrong password (`401`), missing credentials (`400`), Pydantic schema validation (`422`), missing/invalid JWT (`401`), unknown gateway route (`404`), `/internal/auth/verify` |
| `test_05_crud_validation_404_and_business_edge_cases` | Full CRUD for addresses (`201/200/204/404/422`), restaurants (`201/200/404/409`), categories & menu items (update, availability toggle, soft-delete, `403/404`), free delivery fee threshold (`>= INR 500`), unavailable item (`400`), closed restaurant (`400`), early agent assignment (`409`), order rejection (`REJECTED`), non-participant rating (`403`), and report RBAC (`403`) |

---

## 2. Frontend React Tests (Vitest + React Testing Library)

### Commands
```bash
cd frontend
npm test
npm run lint
npm run build
```

### Results Summary
- **Vitest + RTL:** `4 test files passed (4)`, **`9 tests passed (9)`** in `5.66s`
  - `src/__tests__/LoginPage.test.jsx` (2 tests): client-side required/email/password validation + API error display on failed login
  - `src/__tests__/ProtectedRoute.test.jsx` (3 tests): unauthenticated redirect to `/login`, unauthorized role `403 — Access Denied`, authorized role access
  - `src/__tests__/RestaurantsPage.test.jsx` (2 tests): API listing render + error alert on network/service failure
  - `src/__tests__/RestaurantForm.test.jsx` (2 tests): required field validation + formatted payload submission
- **ESLint:** `0 errors, 0 warnings`
- **Vite Production Build:** Succeeds cleanly (`dist/` generated in ~1s)

---

## 3. Alembic Migration Verification

Every microservice's Alembic migration suite was verified with `upgrade head -> downgrade base -> upgrade head` on clean databases:
- `auth-service` (`001_initial_auth`) — PASS
- `user-service` (`001_initial_user`) — PASS
- `restaurant-service` (`001_initial_restaurant`) — PASS
- `menu-service` (`001_initial_menu`) — PASS
- `order-service` (`001_initial_order`) — PASS
- `delivery-service` (`001_initial_delivery`) — PASS
- `rating-service` (`001_initial_rating`) — PASS
- `report-service` (`001_initial_report`) — PASS

---

## 4. Known Testing Gaps

- Unhandled `500` database failure branches and `503` downstream network-timeout branches in inter-service `httpx` clients account for most of the remaining 10% uncovered lines.
- Browser-level E2E automation (Playwright/Cypress) against live servers is not included; frontend integration is validated with Vitest + React Testing Library against mocked Axios responses while backend E2E tests exercise the full multi-service stack.
