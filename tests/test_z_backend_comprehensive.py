from decimal import Decimal
import httpx


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client: httpx.Client, email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_04_auth_security_validation_and_gateway_errors(client: httpx.Client, microservices_cluster):
    # Wrong password -> 401
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["code"] == "INVALID_CREDENTIALS"

    # Missing credentials -> 400
    empty_login = client.post("/api/v1/auth/login", json={})
    assert empty_login.status_code == 400
    assert empty_login.json()["code"] == "CREDENTIALS_MISSING"

    # Malformed email -> 422
    bad_reg = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "123", "full_name": "A", "phone": "abc"},
    )
    assert bad_reg.status_code == 422

    # Missing bearer token -> 401
    no_auth = client.get("/api/v1/customer/profile")
    assert no_auth.status_code == 401
    assert no_auth.json()["code"] == "AUTHENTICATION_REQUIRED"

    # Tampered JWT -> 401
    bad_jwt = client.get("/api/v1/customer/profile", headers=_auth("invalid.jwt.token"))
    assert bad_jwt.status_code == 401
    assert bad_jwt.json()["code"] == "INVALID_TOKEN"

    # Unknown API route on Gateway -> 404
    unknown = client.get("/api/v1/does-not-exist")
    assert unknown.status_code == 404
    assert unknown.json()["code"] == "ROUTE_NOT_FOUND"

    # Internal auth verify endpoint
    admin_token = _login(client, "admin@test.com", "Admin@123")
    with httpx.Client(base_url=microservices_cluster["service_urls"]["auth"], timeout=5.0) as auth_cli:
        ok = auth_cli.get(
            "/internal/auth/verify",
            headers={
                "X-Internal-API-Key": microservices_cluster["internal_key"],
                "Authorization": f"Bearer {admin_token}",
            },
        )
        assert ok.status_code == 200
        assert ok.json()["role"] == "ADMIN"

        missing_bearer = auth_cli.get(
            "/internal/auth/verify",
            headers={"X-Internal-API-Key": microservices_cluster["internal_key"]},
        )
        assert missing_bearer.status_code == 401


def test_05_crud_validation_404_and_business_edge_cases(client: httpx.Client):
    admin_token = _login(client, "admin@test.com", "Admin@123")
    owner1_token = _login(client, "owner1@test.com", "Password@1")
    owner2_token = _login(client, "owner2@test.com", "Password@1")
    cust1_token = _login(client, "cust1@test.com", "Password@1")
    cust2_token = _login(client, "cust2@test.com", "Password@1")

    # Customer profile GET + address full CRUD + 404 + 422
    prof = client.get("/api/v1/customer/profile", headers=_auth(cust1_token))
    assert prof.status_code == 200

    bad_addr = client.post(
        "/api/v1/addresses",
        headers=_auth(cust1_token),
        json={"line1": "OK Street", "city": "Bengaluru", "pincode": "000000"},
    )
    assert bad_addr.status_code == 422

    addr2 = client.post(
        "/api/v1/addresses",
        headers=_auth(cust1_token),
        json={"line1": "456 Park Ave", "city": "Bengaluru", "pincode": "560001", "is_default": False},
    )
    assert addr2.status_code == 201
    addr2_id = addr2.json()["id"]

    listed = client.get("/api/v1/addresses", headers=_auth(cust1_token))
    assert listed.status_code == 200
    assert len(listed.json()) >= 2

    set_def = client.put(f"/api/v1/addresses/{addr2_id}/default", headers=_auth(cust1_token))
    assert set_def.status_code == 200
    assert set_def.json()["is_default"] is True

    del_addr = client.delete(f"/api/v1/addresses/{addr2_id}", headers=_auth(cust1_token))
    assert del_addr.status_code == 204

    not_found_addr = client.delete("/api/v1/addresses/99999", headers=_auth(cust1_token))
    assert not_found_addr.status_code == 404

    # Restaurant GET/PUT/PATCH/duplicate 409/404
    my_rest = client.get("/api/v1/restaurants/me", headers=_auth(owner1_token))
    assert my_rest.status_code == 200
    rest1_id = my_rest.json()["id"]

    dup_rest = client.post(
        "/api/v1/restaurants",
        headers=_auth(owner1_token),
        json={
            "name": "Duplicate Rest",
            "cuisine": "Indian",
            "city": "Bengaluru",
            "address": "123 Street",
            "opens_at": "09:00:00",
            "closes_at": "22:00:00",
        },
    )
    assert dup_rest.status_code == 409

    upd_rest = client.put(
        "/api/v1/restaurants/me",
        headers=_auth(owner1_token),
        json={"name": "Spice Junction Prime"},
    )
    assert upd_rest.status_code == 200
    assert upd_rest.json()["name"] == "Spice Junction Prime"

    missing_rest = client.get("/api/v1/restaurants/99999")
    assert missing_rest.status_code == 404

    # Menu Category & Menu Item full CRUD (update, availability toggle, soft delete, 404)
    cats = client.get("/api/v1/restaurants/me/menu-categories", headers=_auth(owner1_token))
    assert cats.status_code == 200
    assert len(cats.json()) >= 1

    temp_cat = client.post(
        "/api/v1/restaurants/me/menu-categories",
        headers=_auth(owner1_token),
        json={"name": "Desserts", "display_order": 5},
    )
    assert temp_cat.status_code == 201
    temp_cat_id = temp_cat.json()["id"]

    upd_cat = client.put(
        f"/api/v1/restaurants/me/menu-categories/{temp_cat_id}",
        headers=_auth(owner1_token),
        json={"name": "Artisan Desserts"},
    )
    assert upd_cat.status_code == 200
    assert upd_cat.json()["name"] == "Artisan Desserts"

    # Owner 2 cannot delete Owner 1's category -> 403
    cat_idor = client.delete(
        f"/api/v1/restaurants/me/menu-categories/{temp_cat_id}",
        headers=_auth(owner2_token),
    )
    assert cat_idor.status_code == 403

    temp_item = client.post(
        "/api/v1/restaurants/me/menu-items",
        headers=_auth(owner1_token),
        json={"category_id": temp_cat_id, "name": "Gulab Jamun", "price": "300.00"},
    )
    assert temp_item.status_code == 201
    temp_item_id = temp_item.json()["id"]

    # Update item & toggle availability off -> ordering unavailable item fails with 400
    upd_item = client.put(
        f"/api/v1/menu-items/{temp_item_id}",
        headers=_auth(owner1_token),
        json={"price": "320.00"},
    )
    assert upd_item.status_code == 200
    assert Decimal(upd_item.json()["price"]) == Decimal("320.00")

    toggle_off = client.patch(
        f"/api/v1/menu-items/{temp_item_id}/availability",
        headers=_auth(owner1_token),
        json={"is_available": False},
    )
    assert toggle_off.status_code == 200
    assert toggle_off.json()["is_available"] is False

    # Customer gets valid address ID
    c1_addr_id = client.get("/api/v1/addresses", headers=_auth(cust1_token)).json()[0]["id"]

    unavail_order = client.post(
        "/api/v1/orders",
        headers=_auth(cust1_token),
        json={
            "restaurant_id": rest1_id,
            "address_id": c1_addr_id,
            "items": [{"menu_item_id": temp_item_id, "quantity": 1}],
        },
    )
    assert unavail_order.status_code == 400
    assert unavail_order.json()["code"] == "ITEM_UNAVAILABLE"

    # Re-enable item, place high-value order (>= 500 -> FREE delivery fee!)
    client.patch(
        f"/api/v1/menu-items/{temp_item_id}/availability",
        headers=_auth(owner1_token),
        json={"is_available": True},
    )
    free_deliv_order = client.post(
        "/api/v1/orders",
        headers=_auth(cust1_token),
        json={
            "restaurant_id": rest1_id,
            "address_id": c1_addr_id,
            "items": [{"menu_item_id": temp_item_id, "quantity": 2}],
        },
    )
    assert free_deliv_order.status_code == 201
    assert Decimal(free_deliv_order.json()["item_total"]) == Decimal("640.00")
    assert Decimal(free_deliv_order.json()["delivery_fee"]) == Decimal("0.00")
    ord_reject_id = free_deliv_order.json()["id"]

    # Assign agent while still PLACED -> 409 Conflict
    early_assign = client.patch(
        f"/api/v1/orders/{ord_reject_id}/assign-agent",
        headers=_auth(admin_token),
        json={"agent_id": 4},
    )
    assert early_assign.status_code == 409

    # Restaurant owner rejects order & lists incoming orders
    rej = client.patch(
        f"/api/v1/orders/{ord_reject_id}/status",
        headers=_auth(owner1_token),
        json={"status": "REJECTED", "remark": "Out of ingredients"},
    )
    assert rej.status_code == 200
    assert rej.json()["status"] == "REJECTED"

    my_orders = client.get("/api/v1/orders/me", headers=_auth(cust1_token))
    assert my_orders.status_code == 200
    assert my_orders.json()["total"] >= 3

    rest_orders = client.get("/api/v1/orders/restaurant?status=REJECTED", headers=_auth(owner1_token))
    assert rest_orders.status_code == 200
    assert rest_orders.json()["total"] == 1

    # Soft delete menu item & delete temporary category
    soft_del = client.delete(f"/api/v1/menu-items/{temp_item_id}", headers=_auth(owner1_token))
    assert soft_del.status_code == 200
    assert soft_del.json()["is_deleted"] is True

    del_cat = client.delete(
        f"/api/v1/restaurants/me/menu-categories/{temp_cat_id}",
        headers=_auth(owner1_token),
    )
    assert del_cat.status_code == 204

    # Close restaurant -> ordering fails with 400 RESTAURANT_CLOSED
    client.patch("/api/v1/restaurants/me/open-status", headers=_auth(owner1_token), json={"is_open": False})
    closed_order = client.post(
        "/api/v1/orders",
        headers=_auth(cust1_token),
        json={"restaurant_id": rest1_id, "address_id": c1_addr_id, "items": [{"menu_item_id": 1, "quantity": 1}]},
    )
    assert closed_order.status_code == 400
    assert closed_order.json()["code"] == "RESTAURANT_CLOSED"
    # Re-open restaurant
    client.patch("/api/v1/restaurants/me/open-status", headers=_auth(owner1_token), json={"is_open": True})

    # Order 404, Rating 403/404, Reports 403 for customer & Admin filtered sales
    assert client.get("/api/v1/orders/99999", headers=_auth(admin_token)).status_code == 404
    assert client.post(
        "/api/v1/orders/1/rating",
        headers=_auth(cust2_token),
        json={"restaurant_rating": 5, "agent_rating": 5},
    ).status_code == 403
    assert client.get("/api/v1/reports/cancellation-rate", headers=_auth(cust1_token)).status_code == 403
    admin_sales = client.get(f"/api/v1/reports/restaurant-sales?restaurant_id={rest1_id}", headers=_auth(admin_token))
    assert admin_sales.status_code == 200
    assert admin_sales.json()["restaurant_id"] == rest1_id
