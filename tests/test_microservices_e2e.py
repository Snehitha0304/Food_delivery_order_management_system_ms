import sqlite3
from decimal import Decimal
import httpx


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client: httpx.Client, email: str, password: str, use_form: bool = False) -> dict:
    if use_form:
        resp = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    else:
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("X-Served-By") == "auth-service"
    return resp.json()


def test_01_gateway_health_and_database_per_service_isolation(client: httpx.Client, microservices_cluster):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["gateway"] == "healthy"
    assert set(body["services"].keys()) == {
        "auth-service",
        "user-service",
        "restaurant-service",
        "menu-service",
        "order-service",
        "delivery-service",
        "rating-service",
        "report-service",
    }
    for svc_health in body["services"].values():
        assert svc_health["status"] == "healthy"
        assert svc_health["database"] == "connected"

    # Verify Gateway unified Swagger UI & OpenAPI schema aggregate all 8 services (including Delivery & Ratings)
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200
    assert "swagger-ui" in docs_resp.text.lower()

    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    openapi_paths = openapi_resp.json()["paths"]
    assert "/api/v1/orders/{id}/assign-agent" in openapi_paths
    assert "/api/v1/orders/agent" in openapi_paths
    assert "/api/v1/orders/{id}/delivery-status" in openapi_paths
    assert "/api/v1/orders/{id}/rating" in openapi_paths
    assert "/api/v1/auth/login" in openapi_paths
    assert "/api/v1/restaurants/{id}/menu" in openapi_paths
    assert "/api/v1/reports/restaurant-sales" in openapi_paths

    # Verify each of the 8 databases exists separately and ONLY contains its own domain tables
    expected_tables = {
        "auth": {"auth_credentials", "login_audit_logs"},
        "user": {"users", "addresses"},
        "restaurant": {"restaurants"},
        "menu": {"menu_categories", "menu_items"},
        "order": {"orders", "order_items", "order_status_history"},
        "delivery": {"deliveries", "delivery_events"},
        "rating": {"ratings"},
        "report": {"report_snapshots"},
    }
    for svc_key, expected in expected_tables.items():
        db_file = microservices_cluster["db_paths"][svc_key]
        conn = sqlite3.connect(db_file)
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            }
        finally:
            conn.close()
        assert tables == expected, f"{svc_key}_db tables mismatch: {tables} != {expected}"


def test_02_internal_endpoints_security_protection(client: httpx.Client, microservices_cluster):
    # Gateway must block external calls to /internal/*
    gw_resp = client.get("/internal/users/1")
    assert gw_resp.status_code == 403
    assert gw_resp.json()["code"] == "INTERNAL_ROUTE_FORBIDDEN"

    # Direct microservice internal call without API key must return 401
    user_url = microservices_cluster["service_urls"]["user"]
    with httpx.Client(base_url=user_url, timeout=5.0) as direct_client:
        no_key_resp = direct_client.get("/internal/users/1")
        assert no_key_resp.status_code == 401
        assert no_key_resp.json()["code"] == "INVALID_INTERNAL_API_KEY"

        # With valid internal API key it succeeds
        ok_resp = direct_client.get(
            "/internal/users/1",
            headers={"X-Internal-API-Key": microservices_cluster["internal_key"]},
        )
        assert ok_resp.status_code == 200
        assert ok_resp.json()["email"] == "admin@test.com"


def test_03_full_end_to_end_food_delivery_workflow(client: httpx.Client, microservices_cluster):
    # 1. Admin login (test OAuth2 form login)
    admin_token = _login(client, "admin@test.com", "Admin@123", use_form=True)["access_token"]

    # 2. Admin onboards 2 restaurant owners & 2 delivery agents
    owner1 = client.post(
        "/api/v1/auth/admin/users",
        headers=_auth_header(admin_token),
        json={
            "email": "owner1@test.com",
            "password": "Password@1",
            "full_name": "Owner One",
            "phone": "+919800000001",
            "role": "RESTAURANT_OWNER",
        },
    )
    assert owner1.status_code == 201, owner1.text

    owner2 = client.post(
        "/api/v1/auth/admin/users",
        headers=_auth_header(admin_token),
        json={
            "email": "owner2@test.com",
            "password": "Password@1",
            "full_name": "Owner Two",
            "phone": "+919800000002",
            "role": "RESTAURANT_OWNER",
        },
    )
    assert owner2.status_code == 201

    agent1 = client.post(
        "/api/v1/auth/admin/users",
        headers=_auth_header(admin_token),
        json={
            "email": "agent1@test.com",
            "password": "Password@1",
            "full_name": "Agent One",
            "phone": "+919800000003",
            "role": "DELIVERY_AGENT",
        },
    )
    assert agent1.status_code == 201
    agent1_id = agent1.json()["id"]

    agent2 = client.post(
        "/api/v1/auth/admin/users",
        headers=_auth_header(admin_token),
        json={
            "email": "agent2@test.com",
            "password": "Password@1",
            "full_name": "Agent Two",
            "phone": "+919800000004",
            "role": "DELIVERY_AGENT",
        },
    )
    assert agent2.status_code == 201

    # 3. Two customers self-register
    cust1 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "cust1@test.com",
            "password": "Password@1",
            "full_name": "Customer One",
            "phone": "+919800000011",
        },
    )
    assert cust1.status_code == 201

    # Duplicate email -> 409
    dup_cust = client.post(
        "/api/v1/auth/register",
        json={
            "email": "cust1@test.com",
            "password": "Password@1",
            "full_name": "Customer One",
            "phone": "+919800000011",
        },
    )
    assert dup_cust.status_code == 409

    cust2 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "cust2@test.com",
            "password": "Password@1",
            "full_name": "Customer Two",
            "phone": "+919800000012",
        },
    )
    assert cust2.status_code == 201

    # Log in all roles (JSON login)
    owner1_token = _login(client, "owner1@test.com", "Password@1")["access_token"]
    owner2_token = _login(client, "owner2@test.com", "Password@1")["access_token"]
    agent1_token = _login(client, "agent1@test.com", "Password@1")["access_token"]
    agent2_token = _login(client, "agent2@test.com", "Password@1")["access_token"]
    cust1_token = _login(client, "cust1@test.com", "Password@1")["access_token"]
    cust2_token = _login(client, "cust2@test.com", "Password@1")["access_token"]

    # 4. Customer profile & address management
    prof = client.put(
        "/api/v1/customer/profile",
        headers=_auth_header(cust1_token),
        json={"full_name": "Customer One Updated"},
    )
    assert prof.status_code == 200
    assert prof.json()["full_name"] == "Customer One Updated"

    addr1 = client.post(
        "/api/v1/addresses",
        headers=_auth_header(cust1_token),
        json={"line1": "123 Main St", "city": "Bengaluru", "pincode": "560038", "is_default": True},
    )
    assert addr1.status_code == 201
    addr1_id = addr1.json()["id"]

    # Customer 2 cannot delete Customer 1's address -> 403
    del_idor = client.delete(f"/api/v1/addresses/{addr1_id}", headers=_auth_header(cust2_token))
    assert del_idor.status_code == 403

    # 5. Restaurant & Menu setup (restaurant-service)
    # RBAC check: Customer cannot create restaurant -> 403
    rbac_fail = client.post(
        "/api/v1/restaurants",
        headers=_auth_header(cust1_token),
        json={
            "name": "Bad Rest",
            "cuisine": "Indian",
            "city": "Bengaluru",
            "address": "10 Street",
            "opens_at": "09:00:00",
            "closes_at": "22:00:00",
        },
    )
    assert rbac_fail.status_code == 403

    rest1 = client.post(
        "/api/v1/restaurants",
        headers=_auth_header(owner1_token),
        json={
            "name": "Spice Junction",
            "cuisine": "Indian",
            "city": "Bengaluru",
            "address": "12 Indiranagar",
            "opens_at": "09:00:00",
            "closes_at": "23:00:00",
            "is_open": True,
        },
    )
    assert rest1.status_code == 201, rest1.text
    rest1_id = rest1.json()["id"]

    rest2 = client.post(
        "/api/v1/restaurants",
        headers=_auth_header(owner2_token),
        json={
            "name": "Pizza Roma",
            "cuisine": "Italian",
            "city": "Bengaluru",
            "address": "45 Koramangala",
            "opens_at": "11:00:00",
            "closes_at": "23:00:00",
            "is_open": True,
        },
    )
    assert rest2.status_code == 201

    cat1 = client.post(
        "/api/v1/restaurants/me/menu-categories",
        headers=_auth_header(owner1_token),
        json={"name": "Mains", "display_order": 1},
    )
    assert cat1.status_code == 201
    cat1_id = cat1.json()["id"]

    item1 = client.post(
        "/api/v1/restaurants/me/menu-items",
        headers=_auth_header(owner1_token),
        json={
            "category_id": cat1_id,
            "name": "Paneer Butter Masala",
            "price": "200.00",
            "is_veg": True,
            "is_available": True,
        },
    )
    assert item1.status_code == 201
    item1_id = item1.json()["id"]

    # Ownership check: Owner 2 cannot edit Owner 1's menu item -> 403
    edit_other = client.put(
        f"/api/v1/menu-items/{item1_id}",
        headers=_auth_header(owner2_token),
        json={"price": "10.00"},
    )
    assert edit_other.status_code == 403
    assert edit_other.json()["code"] == "ITEM_OWNERSHIP_VIOLATION"

    # Search restaurants & view grouped menu
    search_resp = client.get("/api/v1/restaurants?city=Bengaluru&cuisine=Indian")
    assert search_resp.status_code == 200
    assert search_resp.json()["total"] == 1

    menu_resp = client.get(f"/api/v1/restaurants/{rest1_id}/menu")
    assert menu_resp.status_code == 200
    assert menu_resp.headers.get("X-Served-By") == "menu-service"
    assert len(menu_resp.json()["categories"][0]["items"]) == 1

    # 6. Order creation with PRICE TAMPERING attempt (order-service -> restaurant-service + user-service)
    # Real price = 200.00 * 2 = 400.00; 5% tax = 20.00; delivery fee (< 500) = 40.00; grand_total = 460.00
    order1 = client.post(
        "/api/v1/orders",
        headers=_auth_header(cust1_token),
        json={
            "restaurant_id": rest1_id,
            "address_id": addr1_id,
            "items": [{"menu_item_id": item1_id, "quantity": 2, "price": "1.00"}],
        },
    )
    assert order1.status_code == 201, order1.text
    order1_data = order1.json()
    order1_id = order1_data["id"]
    assert Decimal(order1_data["item_total"]) == Decimal("400.00")
    assert Decimal(order1_data["tax_amount"]) == Decimal("20.00")
    assert Decimal(order1_data["delivery_fee"]) == Decimal("40.00")
    assert Decimal(order1_data["grand_total"]) == Decimal("460.00")
    assert order1_data["status"] == "PLACED"

    # Place a 2nd order and cancel it (tests cancellation flow & report metrics)
    order2 = client.post(
        "/api/v1/orders",
        headers=_auth_header(cust1_token),
        json={
            "restaurant_id": rest1_id,
            "address_id": addr1_id,
            "items": [{"menu_item_id": item1_id, "quantity": 1}],
        },
    )
    assert order2.status_code == 201
    order2_id = order2.json()["id"]
    cancel_resp = client.patch(f"/api/v1/orders/{order2_id}/cancel", headers=_auth_header(cust1_token))
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    # 7. IDOR check: Customer 2 cannot view Customer 1's order -> 403
    idor_order = client.get(f"/api/v1/orders/{order1_id}", headers=_auth_header(cust2_token))
    assert idor_order.status_code == 403
    assert idor_order.json()["code"] == "ORDER_ACCESS_FORBIDDEN"

    # 8. State Machine violation: PLACED -> READY_FOR_PICKUP must return 409 Conflict
    bad_transition = client.patch(
        f"/api/v1/orders/{order1_id}/status",
        headers=_auth_header(owner1_token),
        json={"status": "READY_FOR_PICKUP"},
    )
    assert bad_transition.status_code == 409
    assert bad_transition.json()["code"] == "INVALID_STATUS_TRANSITION"

    # Valid restaurant transitions: PLACED -> CONFIRMED -> PREPARING -> READY_FOR_PICKUP
    for next_status in ["CONFIRMED", "PREPARING", "READY_FOR_PICKUP"]:
        tr = client.patch(
            f"/api/v1/orders/{order1_id}/status",
            headers=_auth_header(owner1_token),
            json={"status": next_status},
        )
        assert tr.status_code == 200, tr.text
        assert tr.json()["status"] == next_status

    # Customer cannot cancel once READY_FOR_PICKUP -> 409
    late_cancel = client.patch(f"/api/v1/orders/{order1_id}/cancel", headers=_auth_header(cust1_token))
    assert late_cancel.status_code == 409

    # 9. Delivery assignment via delivery-service
    assign_resp = client.patch(
        f"/api/v1/orders/{order1_id}/assign-agent",
        headers=_auth_header(admin_token),
        json={"agent_id": agent1_id},
    )
    assert assign_resp.status_code == 200, assign_resp.text
    assert assign_resp.json()["agent_id"] == agent1_id

    # Privacy check: Agent 1 views order BEFORE PICKED_UP -> customer_phone must be None
    pre_pickup_detail = client.get(f"/api/v1/orders/{order1_id}", headers=_auth_header(agent1_token))
    assert pre_pickup_detail.status_code == 200
    assert pre_pickup_detail.json()["customer_phone"] is None

    # Unassigned Agent 2 cannot update delivery status -> 403
    unassigned_pickup = client.patch(
        f"/api/v1/orders/{order1_id}/delivery-status",
        headers=_auth_header(agent2_token),
        json={"status": "PICKED_UP"},
    )
    assert unassigned_pickup.status_code == 403
    assert unassigned_pickup.json()["code"] == "NOT_ASSIGNED_AGENT"

    # Agent 1 lists assigned orders
    agent_orders = client.get("/api/v1/orders/agent", headers=_auth_header(agent1_token))
    assert agent_orders.status_code == 200
    assert agent_orders.json()["total"] == 1

    # Agent 1 marks PICKED_UP
    pickup = client.patch(
        f"/api/v1/orders/{order1_id}/delivery-status",
        headers=_auth_header(agent1_token),
        json={"status": "PICKED_UP"},
    )
    assert pickup.status_code == 200
    assert pickup.json()["status"] == "PICKED_UP"

    # Privacy check: Agent 1 views order AFTER PICKED_UP -> customer_phone is now visible
    post_pickup_detail = client.get(f"/api/v1/orders/{order1_id}", headers=_auth_header(agent1_token))
    assert post_pickup_detail.status_code == 200
    assert post_pickup_detail.json()["customer_phone"] == "+919800000011"

    # Rating BEFORE DELIVERED -> 400
    early_rating = client.post(
        f"/api/v1/orders/{order1_id}/rating",
        headers=_auth_header(cust1_token),
        json={"restaurant_rating": 5, "agent_rating": 5},
    )
    assert early_rating.status_code == 400
    assert early_rating.json()["code"] == "ORDER_NOT_DELIVERED"

    # Agent 1 marks DELIVERED
    delivered = client.patch(
        f"/api/v1/orders/{order1_id}/delivery-status",
        headers=_auth_header(agent1_token),
        json={"status": "DELIVERED"},
    )
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "DELIVERED"
    assert delivered.json()["delivered_at"] is not None

    # 10. Rating via rating-service -> recomputes restaurant.avg_rating in restaurant-service
    rating_resp = client.post(
        f"/api/v1/orders/{order1_id}/rating",
        headers=_auth_header(cust1_token),
        json={"restaurant_rating": 5, "agent_rating": 4, "comment": "Great food!"},
    )
    assert rating_resp.status_code == 201, rating_resp.text

    # Duplicate rating -> 409
    dup_rating = client.post(
        f"/api/v1/orders/{order1_id}/rating",
        headers=_auth_header(cust1_token),
        json={"restaurant_rating": 3, "agent_rating": 3},
    )
    assert dup_rating.status_code == 409

    # Verify restaurant.avg_rating was updated in restaurant_db
    rest_after = client.get(f"/api/v1/restaurants/{rest1_id}")
    assert rest_after.status_code == 200
    assert Decimal(rest_after.json()["avg_rating"]) == Decimal("5.00")

    # 11. Reports via report-service (aggregates user + restaurant + order + rating services)
    sales_resp = client.get("/api/v1/reports/restaurant-sales", headers=_auth_header(owner1_token))
    assert sales_resp.status_code == 200, sales_resp.text
    sales = sales_resp.json()
    assert sales["restaurant_id"] == rest1_id
    assert sales["total_orders"] == 2
    assert sales["completed_orders"] == 1
    assert sales["cancelled_orders"] == 1
    assert Decimal(sales["total_revenue"]) == Decimal("460.00")

    perf_resp = client.get("/api/v1/reports/agent-performance", headers=_auth_header(admin_token))
    assert perf_resp.status_code == 200, perf_resp.text
    perf_map = {row["agent_id"]: row for row in perf_resp.json()}
    assert perf_map[agent1_id]["total_assigned"] == 1
    assert perf_map[agent1_id]["total_delivered"] == 1
    assert Decimal(perf_map[agent1_id]["avg_rating"]) == Decimal("4.00")

    cancel_rate_resp = client.get("/api/v1/reports/cancellation-rate", headers=_auth_header(admin_token))
    assert cancel_rate_resp.status_code == 200
    cr = cancel_rate_resp.json()
    assert cr["total_orders"] == 2
    assert cr["cancelled_orders"] == 1
    assert Decimal(cr["cancellation_rate_percentage"]) == Decimal("50.0")

    # Verify auth_db, delivery_db & report_db actually persisted records in their own databases
    aconn = sqlite3.connect(microservices_cluster["db_paths"]["auth"])
    try:
        assert aconn.execute("SELECT COUNT(*) FROM auth_credentials").fetchone()[0] >= 7
        assert aconn.execute("SELECT COUNT(*) FROM login_audit_logs WHERE success = 1").fetchone()[0] >= 7
    finally:
        aconn.close()

    dconn = sqlite3.connect(microservices_cluster["db_paths"]["delivery"])
    try:
        assert dconn.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0] == 1
        assert dconn.execute("SELECT COUNT(*) FROM delivery_events").fetchone()[0] == 3
    finally:
        dconn.close()

    rconn = sqlite3.connect(microservices_cluster["db_paths"]["report"])
    try:
        assert rconn.execute("SELECT COUNT(*) FROM report_snapshots").fetchone()[0] == 3
    finally:
        rconn.close()
