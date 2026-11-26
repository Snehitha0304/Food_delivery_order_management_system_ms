# Design Decisions, Trade-offs & Known Limitations

## 1. Architectural Design Decisions

### Microservices & Database-per-Service Decomposition
- **Decision:** Decomposed the monolith into **8 bounded-context microservices** (`auth-service`, `user-service`, `restaurant-service`, `menu-service`, `order-service`, `delivery-service`, `rating-service`, `report-service`) behind a stateless **API Gateway** (`api-gateway`).
- **Rationale:** Each service owns its schema, ORM models, repositories, and Alembic migrations (`auth_db` through `report_db`). No cross-database SQL joins or cross-DB foreign keys exist, allowing each database engine (SQLite, MySQL 8.0, or PostgreSQL 16) to be swapped purely via `.env` configuration.
- **Trade-off:** Operations spanning multiple domains (e.g., placing an order or generating agent performance reports) require synchronous HTTP calls over internal APIs, increasing latency compared to an in-process monolith join.

### Security Architecture
- **Stateless JWT Across Microservices:** `auth-service` hashes passwords with **bcrypt** (`passlib`), records every login attempt in `login_audit_logs`, and issues HS256 JWTs (`sub`, `role`, `email`, `exp`, `iat`). Downstream services verify JWT signatures locally without querying `auth_db` on every request.
- **Internal Service-to-Service Auth:** All `/internal/*` endpoints require a shared `X-Internal-API-Key` header, and the API Gateway explicitly rejects external requests to `/internal/*` (`403 INTERNAL_ROUTE_FORBIDDEN`) and strips any client-supplied `X-Internal-API-Key` header.
- **Defense Against IDOR & Tampering:** Order detail access is restricted to participants (ordering customer, restaurant owner, assigned agent, or admin); customer phone numbers are masked from delivery agents until `PICKED_UP`; client-supplied item prices are ignored in favor of authoritative prices from `menu-service`.

### Layered Code Organization
- Every microservice maintains strict separation of concerns across `core/`, `security/`, `exceptions/`, `models/`, `schemas/`, `repositories/`, `clients/`, `services/`, and `routers/`.
- Centralized exception handlers convert domain `AppException` subclasses and `SQLAlchemyError` into consistent `{"detail": ..., "code": ...}` JSON responses without leaking stack traces or database internals.

### Compensating Transactions
- Because `auth-service` (`auth_db`) and `user-service` (`user_db`) own separate databases, user registration uses a **compensating rollback**: if profile creation in `user-service` fails after credentials are written to `auth_db`, `auth-service` deletes the newly created credential row to avoid orphaned identities.

---

## 2. Known Limitations

1. **Synchronous Inter-Service Calls:** `order-service`, `delivery-service`, `rating-service`, and `report-service` communicate synchronously via `httpx`. If a downstream service is temporarily offline, dependent write endpoints return `503 Service Unavailable`.
2. **Eventual Consistency Without a Message Broker:** Rating average updates (`rating-service -> restaurant-service`) and account provisioning (`auth-service -> user-service`) use direct HTTP calls rather than an asynchronous message queue (Kafka / RabbitMQ) or transactional outbox.
3. **Stateless Token Revocation:** Because downstream services validate JWTs statelessly, deactivating a user in `auth-service` prevents future logins immediately, while existing short-lived tokens remain valid until expiration (default 30 minutes).
4. **In-Memory Rate Limiting:** `slowapi` rate limiting on `auth-service` uses in-memory storage by default (single-instance scope).
5. **Default Local SQLite Mode:** Local quickstart uses 8 separate SQLite files for zero-setup execution; production deployments should use the provided `docker-compose.yml` (PostgreSQL 16) or `docker-compose.mysql.yml` (MySQL 8.0) with strict `CORS_ORIGINS`.

---

## 3. Recommended Next Improvements

- **Asynchronous Event Bus + Outbox Pattern:** Introduce RabbitMQ or Kafka for `OrderDelivered`, `RatingSubmitted`, and `UserRegistered` events to decouple `rating-service`, `report-service`, and notifications.
- **Redis Token Blacklist & Distributed Rate Limiting:** Back `slowapi` and JWT revocation with Redis for multi-replica horizontal scaling.
- **Circuit Breakers & Retries:** Add exponential backoff and circuit-breaker protection around `httpx` clients for transient network failures.
- **OpenTelemetry Distributed Tracing:** Propagate `X-Request-ID` / W3C `traceparent` headers from `api-gateway` across all 8 microservices for end-to-end latency observability.
- **Refresh Tokens & Cookie Storage:** Add HttpOnly refresh tokens for improved XSS resilience on the React frontend.
